# Cloud WAN + Direct Connect — Regional Exit with Automatic Failover

## High-Level Architecture

```
                        ┌─────────────────────────────────────────────────┐
                        │              ON-PREMISES BACKBONE               │
                        │                                                 │
                        │   ┌───────────────┐       ┌───────────────┐    │
                        │   │  DC West       │◄─────►│  DC East       │   │
                        │   │  (10.0.0.0/8)  │  WAN  │  (10.0.0.0/8)  │   │
                        │   └───────┬───────┘       └───────┬───────┘    │
                        └───────────┼───────────────────────┼────────────┘
                                    │                       │
                              DX Connection           DX Connection
                                    │                       │
                              Transit VIF             Transit VIF
                                    │                       │
                           ┌────────┴────────┐    ┌────────┴────────┐
                           │  DX GW West     │    │  DX GW East     │
                           │  (ASN 64600)    │    │  (ASN 64700)    │
                           └────────┬────────┘    └────────┬────────┘
                                    │                       │
                        ─ ─ ─ ─ ─ ─│─ ─ ─ AWS CLOUD WAN ─ ┼─ ─ ─ ─ ─ ─
                                    │                       │
                    Associated      │                       │     Associated
                    with BOTH  ┌────┴─────┐          ┌─────┴────┐  with BOTH
                    CNEs       │ CNE      │  Segment │ CNE      │  CNEs
                           ┌──►│us-west-2 │◄────────►│us-east-1 │◄──┐
                           │   └────┬─────┘  eBGP    └─────┬────┘   │
                           │        │        Mesh          │        │
                           │   ┌────┴─────┐          ┌─────┴────┐   │
                           │   │ VPCs     │          │ VPCs     │   │
                           │   │ West     │          │ East     │   │
                           │   └──────────┘          └──────────┘   │
                           │                                        │
                           └──── Same Segment (e.g. Production) ────┘
```

## Normal State Flow — Local Exit

**us-west-2 VPC → on-prem:**
```
VPC West → CNE us-west-2 → DX GW West → DX → DC West
```
CNE us-west-2 has two routes for 10.0.0.0/8:
- Via local DX GW West: AS_PATH = `[64600]` ← **WINS (shorter)**
- Via remote CNE us-east-1: AS_PATH = `[CNE-east, 64700]` ← longer, not preferred

**us-east-1 VPC → on-prem:**
```
VPC East → CNE us-east-1 → DX GW East → DX → DC East
```
Same logic — local DX GW route has shorter AS_PATH.

**On-prem → AWS (return):**
```
DC West → DX → DX GW West → CNE us-west-2 → VPC West
DC East → DX → DX GW East → CNE us-east-1 → VPC East
```
Each DX GW advertises local CNE routes with shorter AS_PATH. On-prem routers prefer the shorter path naturally.

## Failure State Flow — West DX Goes Down

**us-west-2 VPC → on-prem (failover):**
```
VPC West → CNE us-west-2 → CNE us-east-1 → DX GW East → DX → DC East → backbone → DC West
                            ▲
                            │
                   Only remaining route
                   for 10.0.0.0/8
```

1. West DX goes down → DX GW West stops receiving 10.0.0.0/8 from on-prem
2. That route is withdrawn from CNE us-west-2
3. Only route left: 10.0.0.0/8 via CNE us-east-1 (learned through segment propagation)
4. Traffic crosses Cloud WAN backbone to us-east-1, exits via DX GW East
5. Reaches DC East, then traverses on-prem backbone to DC West if needed

**On-prem → us-west-2 VPCs (return failover):**
```
DC East → DX → DX GW East → CNE us-east-1 → CNE us-west-2 → VPC West
                    ▲
                    │
          DX GW East is associated with
          BOTH CNEs, so it knows us-west-2
          VPC routes (with longer AS_PATH)
```

This is why both DX GWs must be associated with both CNEs — so that DX GW East can advertise us-west-2 VPC prefixes to on-prem during failover. During normal state, on-prem prefers the shorter AS_PATH through the local DX.

## Why No BGP Tuning Needed On-Prem

| At CNE us-west-2 | AS_PATH | Preferred? |
|---|---|---|
| 10.0.0.0/8 via DX GW West (local) | `[64600]` | ✅ Yes — shorter |
| 10.0.0.0/8 via CNE us-east-1 (remote) | `[CNE-east, 64700]` | No — longer |

| At on-prem router (West VPC routes) | AS_PATH | Preferred? |
|---|---|---|
| VPC West CIDRs via DX GW West | `[64600, CNE-west]` | ✅ Yes — shorter |
| VPC West CIDRs via DX GW East | `[64700, CNE-east, CNE-west]` | No — longer |

Cloud WAN's AS_PATH propagation does the work. The customer's on-prem routers just follow standard BGP best path selection — shortest AS_PATH wins — without needing to configure local preference, MED, or AS_PATH prepend.

## Supporting AWS Documentation

### Route Evaluation Order (why local DX GW wins)
Cloud WAN evaluates routes at each CNE in this order: most specific route → static routes → VPC-propagated routes in same Region → AS_PATH length → MED → DX GW routes over remote CNE routes. Since the local DX GW route has a shorter AS_PATH than the route propagated from a remote CNE, the local path always wins.
- https://docs.aws.amazon.com/network-manager/latest/cloudwan/cloudwan-create-attachment.html#cloudwan-route-evaluation

### DX GW Route Propagation (how routes flow in and out)
"Each core network edge associated with the Direct Connect gateway attachment advertises only its local routes towards the Direct Connect gateway." and "The AS_PATH BGP attribute is retained in these route advertisements to your on-premises locations."
- https://docs.aws.amazon.com/network-manager/latest/cloudwan/cloudwan-dxattach-about.html

### Scenario 3 — Same Prefix from Multiple Locations (native DX GW attachment)
Covers using two DX Gateways each associated with a subset of CNEs to control regional exit when both on-prem locations advertise the same summary prefix. Demonstrates AS_PATH-based preference and failover.
- https://aws.amazon.com/blogs/networking-and-content-delivery/simplify-global-hybrid-connectivity-with-aws-cloud-wan-and-aws-direct-connect-integration/

### Scenario 3 — Same Prefix from Multiple Locations (Transit Gateway intermediary)
Older pattern using Transit Gateways between DX and Cloud WAN. Introduces the "behavior-based DX Gateway" concept for controlling regional exit with overlapping prefixes.
- https://aws.amazon.com/blogs/networking-and-content-delivery/advanced-hybrid-routing-scenarios-with-aws-cloud-wan-and-aws-direct-connect/

### Optimal Routing with Cloud WAN (GEO-based segment splitting alternative)
Covers the random CNE selection problem when identical routes are received from multiple remote CNEs, and the GEO-based segment splitting approach as an alternative solution.
- https://aws.amazon.com/blogs/networking-and-content-delivery/achieve-optimal-routing-with-aws-cloud-wan-for-multi-region-networks/

### DX GW and Cloud WAN Core Network Associations
Documents how DX GW attachments are associated with specific CNEs and how regional scoping of the attachment controls which routes are advertised.
- https://docs.amazonaws.cn/en_us/directconnect/latest/UserGuide/direct-connect-cloud-wan.html
