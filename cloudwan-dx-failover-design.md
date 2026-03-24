# Cloud WAN + Direct Connect — Regional Exit with Automatic Failover

## Architecture (3 Regions, 3 DX Gateways)

```
                   ┌──────────────────────────────────────────────────────────────┐
                   │                      ON-PREMISES BACKBONE                    │
                   │                                                              │
                   │   ┌──────────┐       ┌──────────┐       ┌──────────┐        │
                   │   │ DC West  │◄─────►│ DC East  │◄─────►│ DC Sydney│        │
                   │   │10.0.0.0/8│  WAN  │10.0.0.0/8│  WAN  │10.0.0.0/8│        │
                   │   └────┬─────┘       └────┬─────┘       └────┬─────┘        │
                   └────────┼──────────────────┼─────────────────┼───────────────┘
                            │                  │                  │
                       DX West            DX East           DX Sydney
                            │                  │                  │
                   ┌────────┴───────┐ ┌───────┴────────┐ ┌──────┴─────────┐
                   │ DX GW West     │ │ DX GW East     │ │ DX GW Sydney   │
                   │ (ASN 64600)    │ │ (ASN 64700)    │ │ (ASN 64800)    │
                   └────────┬───────┘ └───────┬────────┘ └──────┬─────────┘
                            │                  │                 │
                   ─ ─ ─ ─ ┼─ ─ ─ ─ AWS CLOUD WAN ─ ─ ─ ─ ─ ─┼─ ─ ─ ─ ─
                            │                  │                 │
                      ┌─────┴────┐      ┌─────┴────┐     ┌─────┴──────┐
                      │   CNE    │      │   CNE    │     │   CNE      │
                      │us-west-2 │◄────►│us-east-1 │◄───►│ap-south-2  │
                      └─────┬────┘      └─────┬────┘     └─────┬──────┘
                            │                  │               │
                      ┌─────┴────┐      ┌─────┴────┐     ┌────┴──────┐
                      │ VPCs     │      │ VPCs     │     │ VPCs     │
                      │ West     │      │ East     │     │ Sydney   │
                      └──────────┘      └──────────┘     └──────────┘

                      All CNEs in the same segment (eBGP full mesh)
```

## DX Gateway to CNE Association

| DX Gateway     | Associated CNEs              | Purpose                                         |
|----------------|------------------------------|--------------------------------------------------|
| DX GW West     | us-west-2, us-east-1         | Local for West, backup for East                  |
| DX GW East     | us-east-1, us-west-2         | Local for East, backup for West                  |
| DX GW Sydney   | ap-southeast-2               | Local for Sydney, last resort for US regions     |

Failover priority:
- **us-west-2**: DX GW West → DX GW East → DX GW Sydney (via segment propagation)
- **us-east-1**: DX GW East → DX GW West → DX GW Sydney (via segment propagation)
- **ap-southeast-2**: DX GW Sydney → DX GW West or East (via segment propagation)

---

## Scenario 1: Normal State — All DX Links Up

```
VPC West   → CNE us-west-2    → DX GW West   → DX → DC West
VPC East   → CNE us-east-1    → DX GW East   → DX → DC East
VPC Sydney → CNE ap-south-2   → DX GW Sydney → DX → DC Sydney
```

Each CNE prefers its local DX GW — shortest AS_PATH.

Example — CNE us-west-2 route table for 10.0.0.0/8:

| Route Source              | Type         | AS_PATH              | Preferred? |
|---------------------------|--------------|----------------------|------------|
| DX GW West (associated)  | DX GW route  | `[64600]`            | ✅ Shortest |
| DX GW East (associated)  | DX GW route  | `[64700]`            | No — tied, but West installed first |
| Via CNE ap-south-2        | Remote CNE   | `[CNE-syd, 64800]`   | No — longer path |

---

## Scenario 2: West DX Goes Down — Failover to East

```
VPC West → CNE us-west-2 → DX GW East → DX → DC East → backbone → DC West
```

1. DX GW West loses BGP from on-prem → 10.0.0.0/8 withdrawn
2. CNE us-west-2 still has DX GW East (directly associated) and the remote Sydney CNE path
3. DX GW East wins — directly associated DX GW route beats remote CNE route

CNE us-west-2 route table after West DX failure:

| Route Source              | Type         | AS_PATH              | Preferred? |
|---------------------------|--------------|----------------------|------------|
| DX GW East (associated)  | DX GW route  | `[64700]`            | ✅ Wins     |
| Via CNE ap-south-2        | Remote CNE   | `[CNE-syd, 64800]`   | No          |

---

## Scenario 3: Both US DX Links Down — Failover to Sydney

```
VPC West → CNE us-west-2 → CNE ap-south-2 → DX GW Sydney → DX → DC Sydney → backbone → DC West
```

1. Both DX GW West and DX GW East lose BGP → routes withdrawn
2. CNE us-west-2 only has the route learned via segment propagation from CNE ap-southeast-2
3. Sydney path is the only route left

CNE us-west-2 route table after both US DX failures:

| Route Source              | Type         | AS_PATH              | Preferred? |
|---------------------------|--------------|----------------------|------------|
| Via CNE ap-south-2        | Remote CNE   | `[CNE-syd, 64800]`   | ✅ Only route left |

---

## Key Point: Association Controls Preference, Not Reachability

Even if a DX GW is **not** associated with a CNE, that CNE still learns the route via **segment propagation** (eBGP full mesh between CNEs). The route has a longer AS_PATH and is classified as a "remote CNE route" — lowest priority in evaluation order. This is why Sydney works as a last resort without being associated with the US CNEs.

---

## Cloud WAN Route Evaluation Order

1. Longest prefix match
2. Static routes
3. VPC-propagated routes (same Region)
4. Shortest AS_PATH
5. Lowest MED
6. DX GW-propagated routes > Connect routes > VPN routes > Remote CNE routes
7. If still tied → deterministically random

---

## Supporting AWS Documentation

- **Route Evaluation Order** — https://docs.aws.amazon.com/network-manager/latest/cloudwan/cloudwan-create-attachment.html#cloudwan-route-evaluation
- **DX GW Attachments (route propagation behavior)** — https://docs.aws.amazon.com/network-manager/latest/cloudwan/cloudwan-dxattach-about.html
- **Scenario 3: Same prefix, multiple locations (native DX GW)** — https://aws.amazon.com/blogs/networking-and-content-delivery/simplify-global-hybrid-connectivity-with-aws-cloud-wan-and-aws-direct-connect-integration/
- **Scenario 3: Same prefix, multiple locations (TGW-based)** — https://aws.amazon.com/blogs/networking-and-content-delivery/advanced-hybrid-routing-scenarios-with-aws-cloud-wan-and-aws-direct-connect/
- **Optimal routing with Cloud WAN (GEO segment splitting)** — https://aws.amazon.com/blogs/networking-and-content-delivery/achieve-optimal-routing-with-aws-cloud-wan-for-multi-region-networks/
- **DX GW and Cloud WAN associations** — https://docs.amazonaws.cn/en_us/directconnect/latest/UserGuide/direct-connect-cloud-wan.html
