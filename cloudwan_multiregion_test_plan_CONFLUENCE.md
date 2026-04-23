# AWS Cloud WAN Multi-Region Test Plan

## Table of Contents

- [1. Executive Summary](#1-executive-summary)
- [2. Scope](#2-scope)
  - [2.1 In Scope](#21-in-scope)
  - [2.2 Out of Scope](#22-out-of-scope)
- [3. Prerequisites](#3-prerequisites)
  - [3.1 Test Probe Inventory](#31-test-probe-inventory)
- [4. Test Execution Conventions](#4-test-execution-conventions)
  - [4.1 Test Case ID Format](#41-test-case-id-format)
  - [4.2 Result Codes](#42-result-codes)
  - [4.3 Evidence Required on Failure](#43-evidence-required-on-failure)
- [5. Pre-Test Baseline](#5-pre-test-baseline)
- [6. Intra-Segment Connectivity — Same Region](#6-intra-segment-connectivity--same-region)
  - [6.1 Test Matrix](#61-test-matrix)
- [7. Intra-Segment Connectivity — Cross-Region](#7-intra-segment-connectivity--cross-region)
  - [7.1 Region-Pair Matrix](#71-region-pair-matrix)
- [8. Inter-Segment Isolation (Default-Deny)](#8-inter-segment-isolation-default-deny)
  - [8.1 Test Matrix](#81-test-matrix)
- [9. Inspection Path Enforcement](#9-inspection-path-enforcement)
  - [9.1 Permitted Flow Matrix](#91-permitted-flow-matrix)
  - [9.2 Anti-Test: Inspection Bypass](#92-anti-test-inspection-bypass)
- [10. Shared Services Reachability](#10-shared-services-reachability)
- [11. Hybrid Segment and On-Premises Flows](#11-hybrid-segment-and-on-premises-flows)
  - [11.1 Data Plane — Per-DC Reachability via Both DMZs](#111-data-plane--per-dc-reachability-via-both-dmzs)
  - [11.2 Data Plane — Cross-DMZ Coverage](#112-data-plane--cross-dmz-coverage)
  - [11.3 Control Plane (BGP)](#113-control-plane-bgp)
  - [11.4 Failover](#114-failover)
- [12. M&A Acquisition Flows](#12-ma-acquisition-flows)
- [13. Internet Ingress and Egress Inspection](#13-internet-ingress-and-egress-inspection)
  - [13.1 Egress Inspection](#131-egress-inspection)
  - [13.2 Ingress Inspection — Data Plane](#132-ingress-inspection--data-plane)
  - [13.3 Ingress Security Controls](#133-ingress-security-controls)
  - [13.4 Ingress Anti-Tests](#134-ingress-anti-tests)
  - [13.5 Ingress Failover](#135-ingress-failover)
- [14. Resiliency and Failover](#14-resiliency-and-failover)
- [15. BGP and Routing Validation](#15-bgp-and-routing-validation)
- [16. Logging, Observability, and Alerting](#16-logging-observability-and-alerting)
- [17. Policy and Change Safety](#17-policy-and-change-safety)

---

## 1. Executive Summary

This document defines the validation and acceptance test plan for the AWS Cloud WAN multi-region network environment. The test plan verifies segment isolation, inspection enforcement, hybrid connectivity, M&A onboarding paths, and resiliency across three AWS Regions (us-east-1, us-east-2, us-west-2).

Hybrid validation explicitly covers bidirectional reachability between AWS and the four on-premises data centers via two Secure DMZs, where redundant DX termination routers terminate the Direct Connect circuits before handing traffic to the internal DC fabric. The plan validates per-DMZ and per-DC path reachability, DMZ-level failover, and correct BGP behavior when either Secure DMZ or any DX circuit is withdrawn.

Execution of this plan provides the evidence required to certify the environment for production workload onboarding. Expansion to additional Regions (e.g., ap-southeast-2) is out of scope for this cycle and will be covered by a follow-on addendum.

## 2. Scope

### 2.1 In Scope

- AWS Cloud WAN global network spanning us-east-1, us-east-2, and us-west-2
- Five segments: Prod, Non-Prod, Shared Services, Hybrid, Inspection
- Inter-segment, intra-segment, and cross-region connectivity validation
- On-premises connectivity via Direct Connect / DXGW landing in the Hybrid segment, terminating at redundant DX routers in two Secure DMZs
- Reachability validation to all four on-premises data centers via both Secure DMZs, including per-DMZ and per-DC failover
- M&A acquisition network onboarding paths
- North-south inspection enforcement via regional Inspection VPCs (both egress and ingress directions)
- BGP, routing, failover, and observability validation

### 2.2 Out of Scope

- ap-southeast-2 (Sydney) Region — deferred to a follow-on addendum
- Application-layer functional testing
- Endpoint security, EDR, or host hardening validation
- On-premises LAN/WAN performance outside the Direct Connect demarcation

## 3. Prerequisites

Before executing this plan, confirm the following:

- Core Network Policy deployed and at steady state across all Regions
- All segment VPCs attached to the Core Network Edge (CNE) in their respective Region
- Inspection VPCs deployed and stateful firewalls operational in each Region
- DXGW associations active and BGP sessions Established with on-premises PE routers
- Test probe EC2 instances deployed per Section 3.1 with iperf3, mtr, tcpdump, dig, and curl installed
- Logging enabled: VPC Flow Logs, firewall session logs, Network Manager events
- Change Approval secured for any test requiring route manipulation or policy changes

### 3.1 Test Probe Inventory

| Probe Name | Segment | Region | VPC CIDR | Private IP | Purpose |
|---|---|---|---|---|---|
| probe-prod-use1 | Prod | us-east-1 | | | Intra/cross-segment tests |
| probe-prod-use2 | Prod | us-east-2 | | | Intra/cross-segment tests |
| probe-prod-usw2 | Prod | us-west-2 | | | Intra/cross-segment tests |
| probe-nonprod-use1 | Non-Prod | us-east-1 | | | Isolation & inspection |
| probe-nonprod-use2 | Non-Prod | us-east-2 | | | Isolation & inspection |
| probe-nonprod-usw2 | Non-Prod | us-west-2 | | | Isolation & inspection |
| probe-shared-use1 | Shared Services | us-east-1 | | | DNS, AD, monitoring |
| probe-shared-use2 | Shared Services | us-east-2 | | | DNS, AD, monitoring |
| probe-shared-usw2 | Shared Services | us-west-2 | | | DNS, AD, monitoring |
| probe-hybrid-use1 | Hybrid | us-east-1 | | | On-prem transit |
| probe-onprem-dc1 | On-Prem DC1 | N/A | | | DC1 origin (via Secure DMZ-A) |
| probe-onprem-dc2 | On-Prem DC2 | N/A | | | DC2 origin (via Secure DMZ-A) |
| probe-onprem-dc3 | On-Prem DC3 | N/A | | | DC3 origin (via Secure DMZ-B) |
| probe-onprem-dc4 | On-Prem DC4 | N/A | | | DC4 origin (via Secure DMZ-B) |
| probe-dmz-a | Secure DMZ-A | N/A | | | DX termination path validation |
| probe-dmz-b | Secure DMZ-B | N/A | | | DX termination path validation |

## 4. Test Execution Conventions

### 4.1 Test Case ID Format

`TC-<Section>-<Sequence>`. Example: `TC-05-003` is test case 3 in Section 5.

### 4.2 Result Codes

| Code | Meaning |
|---|---|
| PASS | Observed behavior matches expected result |
| FAIL | Observed behavior does not match expected result; defect raised |
| BLOCKED | Test cannot run due to dependency (capture blocker in Notes) |
| N/A | Test not applicable to this environment |

### 4.3 Evidence Required on Failure

For every FAIL, capture and attach:

- Source and destination IPs, segment names, Region
- Core Network Policy version number
- Relevant segment route table exports
- Firewall session log excerpt
- tcpdump capture where applicable
- Output of AWS Network Manager Route Analyzer for the flow

## 5. Pre-Test Baseline

> **Goal:** Capture a clean-state snapshot of the environment so post-test diffs are meaningful.

| Test ID | Check | Expected Result | Status | Notes |
|---|---|---|---|---|
| TC-05-001 | Export current Core Network Policy JSON | File captured, version recorded | | |
| TC-05-002 | Enumerate CNE attachments per Region | All expected VPC, DXGW, Connect attachments present | | |
| TC-05-003 | Capture segment route tables (all segments, all Regions) | Stored in evidence folder | | |
| TC-05-004 | Capture Inspection VPC route tables and firewall rule set version | Exports stored | | |
| TC-05-005 | Document DXGW associations, BGP ASNs, advertised prefixes | Baseline matches approved design | | |
| TC-05-006 | Confirm VPC Flow Logs, firewall logs, Network Manager events streaming | All log destinations receiving events | | |
| TC-05-007 | Record baseline BGP neighbor states | All neighbors Established | | |

## 6. Intra-Segment Connectivity — Same Region

> **Goal:** Prove two workloads in the same segment and Region communicate directly without transiting the Inspection VPC.

### 6.1 Test Matrix

| Test ID | Source | Destination | Protocol | Expected | Status |
|---|---|---|---|---|---|
| TC-06-001 | probe-prod-use1 | probe-prod-use1-B | ICMP | Reachable, direct path | |
| TC-06-002 | probe-prod-use1 | probe-prod-use1-B | TCP/443 | Reachable both directions | |
| TC-06-003 | probe-prod-use1 | probe-prod-use1-B | TCP/22 | Reachable both directions | |
| TC-06-004 | probe-nonprod-use1 | probe-nonprod-use1-B | ICMP + TCP | Reachable, direct path | |
| TC-06-005 | probe-shared-use1 | probe-shared-use1-B | ICMP + TCP | Reachable, direct path | |
| TC-06-006 | All above | All above | mtr trace | Path does NOT transit Inspection VPC ENIs | |

> **Note:** Intra-segment traffic should not be inspected by policy. If it is, a route is leaking into the Inspection segment.

Repeat the matrix for each Region: us-east-2 and us-west-2.

## 7. Intra-Segment Connectivity — Cross-Region

> **Goal:** Prove Cloud WAN inter-CNE transport works and the segment boundary is preserved across Regions.

### 7.1 Region-Pair Matrix

Execute for each segment where cross-region intra-segment traffic is permitted (Prod, Non-Prod, Shared Services):

| Test ID | Source Region | Dest Region | ICMP | iperf3 (Mbps) | Latency p95 (ms) | In-Seg? | Status |
|---|---|---|---|---|---|---|---|
| TC-07-001 | us-east-1 | us-east-2 | | | | | |
| TC-07-002 | us-east-1 | us-west-2 | | | | | |
| TC-07-003 | us-east-2 | us-west-2 | | | | | |

## 8. Inter-Segment Isolation (Default-Deny)

> **Goal:** Prove segments cannot reach each other without explicit share actions in the Core Network Policy.

### 8.1 Test Matrix

| Test ID | Source | Destination | Scope | Expected | Status |
|---|---|---|---|---|---|
| TC-08-001 | Prod | Non-Prod | Same Region | DENIED | |
| TC-08-002 | Prod | Non-Prod | Cross-Region (all pairs) | DENIED | |
| TC-08-003 | Non-Prod | Prod | Same Region | DENIED | |
| TC-08-004 | Non-Prod | Prod | Cross-Region | DENIED | |
| TC-08-005 | Prod | Hybrid | Any | DENIED unless shared via Inspection | |
| TC-08-006 | Non-Prod | Hybrid | Any | DENIED unless shared via Inspection | |
| TC-08-007 | Non-Prod | Shared Services | Direct (bypass Inspection) | DENIED | |

> **Note:** Failure mode to watch — an overly permissive share-with list in the policy segment-actions block. If a deny test passes unexpectedly, audit segment-actions before anything else.

## 9. Inspection Path Enforcement

> **Goal:** Prove every permitted cross-segment flow is inspected by the stateful firewall.

### 9.1 Permitted Flow Matrix

Verify each flow with firewall session logs AND `tcpdump` on the firewall data interface:

| Test ID | Flow | Scope | Expected Firewall Behavior | Status |
|---|---|---|---|---|
| TC-09-001 | Prod → Shared Services | Same Region | Session logged, allowed | |
| TC-09-002 | Prod → Shared Services | Cross-Region | Session logged (document which Region's FW) | |
| TC-09-003 | Non-Prod → Shared Services | Same + Cross-Region | Session logged, allowed | |
| TC-09-004 | Shared Services → Prod (return) | Any | Symmetric path, same flow | |
| TC-09-005 | Prod → On-Prem via Hybrid | Any | Session logged, allowed | |
| TC-09-006 | On-Prem → Prod | Any | Session logged, allowed | |
| TC-09-007 | Prod us-east-1 → Prod us-west-2 | Cross-Region | Inspected per design [source / dest / both] | |
| TC-09-008 | Block rule injection test | Any allowed flow | Traffic dropped and logged when rule added | |

### 9.2 Anti-Test: Inspection Bypass

| Test ID | Procedure | Expected | Status |
|---|---|---|---|
| TC-09-009 | Add a static route in a segment route table pointing directly at another segment's attachment; attempt traffic | Policy prevents the route, or traffic still forced through Inspection. If traffic bypasses Inspection, FAIL — critical defect | |

## 10. Shared Services Reachability

> **Goal:** Prove core platform services are reachable from all consumer segments across all Regions.

| Test ID | Source | Service | Expected | Status |
|---|---|---|---|---|
| TC-10-001 | Prod (all Regions) | DNS resolver (internal + external names) | Resolution succeeds | |
| TC-10-002 | Non-Prod (all Regions) | DNS resolver | Resolution succeeds | |
| TC-10-003 | Prod (all Regions) | AD LDAP bind | Bind succeeds | |
| TC-10-004 | Non-Prod (all Regions) | AD LDAP bind | Bind succeeds | |
| TC-10-005 | All probes | NTP to Shared Services time source | Sync succeeds | |
| TC-10-006 | All probes | Syslog / CloudWatch agent to log aggregator | Logs arrive at aggregator | |
| TC-10-007 | All probes | Patch / config management endpoint | Reachable | |
| TC-10-008 | probe-prod-usw2 | Cross-Region Shared Services (if centralized) | Latency acceptable for AD auth (document) | |

## 11. Hybrid Segment and On-Premises Flows

> **Goal:** Prove on-premises ↔ AWS traffic flows correctly across four on-premises data centers via two Secure DMZs (DX termination routers), is inspected, and fails over cleanly at both the DX and DMZ levels.

### 11.1 Data Plane — Per-DC Reachability via Both DMZs

| Test ID | Source | Destination | Via DMZ | Expected | Status |
|---|---|---|---|---|---|
| TC-11-001 | probe-prod-use1 | probe-onprem-dc1 | DMZ-A (primary) | Reachable, inspected, uses DMZ-A | |
| TC-11-002 | probe-prod-use1 | probe-onprem-dc2 | DMZ-A (primary) | Reachable, inspected, uses DMZ-A | |
| TC-11-003 | probe-prod-use1 | probe-onprem-dc3 | DMZ-B (primary) | Reachable, inspected, uses DMZ-B | |
| TC-11-004 | probe-prod-use1 | probe-onprem-dc4 | DMZ-B (primary) | Reachable, inspected, uses DMZ-B | |
| TC-11-005 | probe-nonprod-use1 | DC1–DC4 | Per design | Reachable, inspected | |
| TC-11-006 | probe-shared-use1 | DC1–DC4 | Per design | Reachable, inspected | |
| TC-11-007 | On-prem DC1–DC4 | Prod VPC (return) | Symmetric | Return path via same DMZ and firewall | |
| TC-11-008 | On-prem DC1 | Prod in Region without local DX | Via Cloud WAN | Transits Cloud WAN to correct landing Region | |
| TC-11-009 | On-prem DC3 | Prod in Region without local DX | Via Cloud WAN | Transits Cloud WAN to correct landing Region | |

### 11.2 Data Plane — Cross-DMZ Coverage

Prove each DC is reachable through the non-primary DMZ after failover (or that the design intentionally blackholes — document which):

| Test ID | Source | Destination | Forced Path | Expected | Status |
|---|---|---|---|---|---|
| TC-11-010 | probe-prod-use1 | probe-onprem-dc1 | DMZ-B (secondary) | Reachable after DMZ-A withdrawal | |
| TC-11-011 | probe-prod-use1 | probe-onprem-dc2 | DMZ-B (secondary) | Reachable after DMZ-A withdrawal | |
| TC-11-012 | probe-prod-use1 | probe-onprem-dc3 | DMZ-A (secondary) | Reachable after DMZ-B withdrawal | |
| TC-11-013 | probe-prod-use1 | probe-onprem-dc4 | DMZ-A (secondary) | Reachable after DMZ-B withdrawal | |

### 11.3 Control Plane (BGP)

| Test ID | Check | Expected | Status |
|---|---|---|---|
| TC-11-014 | DX BGP neighbors on DMZ-A routers | All Established | |
| TC-11-015 | DX BGP neighbors on DMZ-B routers | All Established | |
| TC-11-016 | Prefixes advertised to on-prem (both DMZs) | Match approved list; no Inspection internals leaked | |
| TC-11-017 | On-prem receives AWS prefixes via DMZ-A | Expected AS-path and communities present | |
| TC-11-018 | On-prem receives AWS prefixes via DMZ-B | Expected AS-path and communities present | |
| TC-11-019 | BGP community tagging for DMZ affinity (DC1/DC2 → DMZ-A, DC3/DC4 → DMZ-B) | Correct primary path selected under steady state | |
| TC-11-020 | AS-path prepending or MED on secondary DMZ | Secondary path less preferred, not equal-cost | |

### 11.4 Failover

| Test ID | Scenario | Expected | Target (s) | Actual | Status |
|---|---|---|---|---|---|
| TC-11-021 | Single DX circuit down on DMZ-A | Traffic fails to surviving DX in same DMZ | [sec] | | |
| TC-11-022 | All DX circuits on DMZ-A down | Traffic fails over to DMZ-B for DC1/DC2 | [sec] | | |
| TC-11-023 | All DX circuits on DMZ-B down | Traffic fails over to DMZ-A for DC3/DC4 | [sec] | | |
| TC-11-024 | Entire Secure DMZ-A offline (router failure) | BGP withdraws; DMZ-B takes all DC traffic | [sec] | | |
| TC-11-025 | Entire Secure DMZ-B offline | BGP withdraws; DMZ-A takes all DC traffic | [sec] | | |
| TC-11-026 | DXGW association withdrawn | Reroute via alternate Region DXGW (split-DXGW) | [sec] | | |
| TC-11-027 | Regional Inspection VPC failure | Hybrid reroutes or fails-closed per design | [sec] | | |
| TC-11-028 | DMZ recovery — return to steady state | Preferred paths restore without blackhole or flap | [sec] | | |

## 12. M&A Acquisition Flows

> **Goal:** Prove acquired networks reach only their approved segments and are always inspected.

| Test ID | Test | Expected | Status |
|---|---|---|---|
| TC-12-001 | M&A network → designated segment | Reachable, inspected | |
| TC-12-002 | M&A network → non-approved segments | DENIED | |
| TC-12-003 | Prod → M&A | Allowed only if explicit in policy | |
| TC-12-004 | M&A with overlapping CIDR | NAT or route filtering behaves per design | |
| TC-12-005 | M&A BGP advertisements | Filtered; do not pollute internal route tables | |
| TC-12-006 | Simulated M&A divestiture (remove connectivity) | Routes withdraw cleanly; no impact to other segments | |

## 13. Internet Ingress and Egress Inspection

> **Goal:** Prove both inbound and outbound internet traffic is forced through the designated Inspection/Ingress path, no local bypass exists, and return paths are symmetric.

> **Note:** Ingress architecture under test — inbound internet traffic lands at a centralized ingress point (Ingress VPC or Inspection VPC public subnets) per Region, passes WAF / IPS inspection, and is forwarded to the destination segment only via inspected paths.

### 13.1 Egress Inspection

| Test ID | Test | Expected | Status |
|---|---|---|---|
| TC-13-001 | Prod workload curl to external host | Succeeds; firewall session logged | |
| TC-13-002 | Non-Prod workload to internet | Succeeds; firewall session logged | |
| TC-13-003 | Workload attempt to reach a local IGW (if present) | Fails, or flagged as policy violation | |
| TC-13-004 | URL filtering / threat prevention rule test domain | Blocked as expected | |
| TC-13-005 | us-west-2 workload egress | Uses us-west-2 Inspection VPC (no hairpin to us-east-1) | |
| TC-13-006 | Egress source IP / NAT | Presents approved public IP / NAT pool per Region | |
| TC-13-007 | Egress DNS resolution path | Uses Shared Services resolver, not public Route 53 direct | |

### 13.2 Ingress Inspection — Data Plane

| Test ID | Test | Expected | Status |
|---|---|---|---|
| TC-13-008 | Inbound HTTPS to Prod public endpoint (each Region) | Lands at Ingress VPC, inspected, forwarded to Prod target | |
| TC-13-009 | Inbound HTTPS to Non-Prod public endpoint | Lands at Ingress VPC, inspected, forwarded to Non-Prod target | |
| TC-13-010 | Inbound traffic attempting to reach Prod via a direct IGW (bypass) | Denied or no route exists; confirmed via route tables | |
| TC-13-011 | Inbound from internet → Shared Services public endpoint (if any) | Inspected; otherwise confirm no public exposure by design | |
| TC-13-012 | Return path for inspected ingress session | Symmetric — returns through same Ingress/Inspection firewall | |
| TC-13-013 | Ingress targeting us-west-2-hosted service | Uses us-west-2 ingress path (no hairpin through us-east-1) | |
| TC-13-014 | Ingress targeting cross-Region backend (client near us-west-2, backend in us-east-1) | Inspected at ingress Region per design; documented path | |

### 13.3 Ingress Security Controls

| Test ID | Test | Expected | Status |
|---|---|---|---|
| TC-13-015 | WAF rule test (SQLi / XSS payload against public endpoint) | Blocked by WAF; logged to SIEM | |
| TC-13-016 | Geo-block rule (if applied) | Requests from blocked geography denied | |
| TC-13-017 | Rate limiting / DDoS protection | Excess requests throttled per policy; Shield/WAF metrics increment | |
| TC-13-018 | TLS inspection / termination point | Matches design (edge-terminated vs passthrough); cert chain valid | |
| TC-13-019 | IPS signature trigger (known malicious pattern) | Blocked and logged | |
| TC-13-020 | Unapproved port/protocol inbound (e.g., inbound SSH from internet) | Denied at ingress firewall | |

### 13.4 Ingress Anti-Tests

| Test ID | Procedure | Expected | Status |
|---|---|---|---|
| TC-13-021 | Attach a public IP / EIP directly to a Prod workload ENI, attempt inbound | Denied by SCP / policy, or traffic still forced through Ingress VPC. Direct reachability = FAIL — critical defect | |
| TC-13-022 | Create an IGW attachment on a segment VPC, attempt inbound flow | Policy prevents creation, or traffic does not reach workload without inspection | |
| TC-13-023 | Asymmetric ingress/egress test (inbound via Ingress VPC, return via different path) | Return forced through same firewall; asymmetric flow = FAIL | |

### 13.5 Ingress Failover

| Test ID | Scenario | Expected | Target (s) | Actual | Status |
|---|---|---|---|---|---|
| TC-13-024 | Single Ingress VPC AZ failure | Traffic fails to surviving AZ; no session blackhole | [sec] | | |
| TC-13-025 | Regional Ingress VPC offline | Per design: DNS failover to alternate Region, or fail-closed | [sec] | | |
| TC-13-026 | WAF / IPS appliance failure | Fails open or closed per policy (document which) | [sec] | | |

## 14. Resiliency and Failover

> **Goal:** Prove the design survives single-component failures within acceptable convergence windows.

| Test ID | Scenario | Expected | Target (s) | Actual | Status |
|---|---|---|---|---|---|
| TC-14-001 | Single AZ failure in Inspection VPC | Failover to other AZ firewall | [sec] | | |
| TC-14-002 | Full regional Inspection VPC failure | Per design: fail-closed or reroute to neighbor Region | [sec] | | |
| TC-14-003 | CNE unreachable in one Region | Cross-Region traffic reroutes or fails per design | [sec] | | |
| TC-14-004 | DXGW failure | Hybrid traffic fails over to backup | [sec] | | |
| TC-14-005 | Asymmetric routing check post-failover | Return path uses same firewall; sessions preserved | N/A | | |

## 15. BGP and Routing Validation

> **Goal:** Prove routing is clean, deterministic, and aligned with intent.

| Test ID | Check | Expected | Status |
|---|---|---|---|
| TC-15-001 | Segment route table audit | Only expected prefixes; no leaks | |
| TC-15-002 | Default route review | Default points to Inspection where required; not to local IGW | |
| TC-15-003 | Prefix counts vs service quotas | Within DXGW and CNE limits | |
| TC-15-004 | MTU end-to-end (standard) | `ping -M do -s 1472` success probe-to-probe and probe-to-on-prem | |
| TC-15-005 | MTU end-to-end (jumbo, if applicable) | Success at design MTU | |
| TC-15-006 | Backup path | Traffic failover through the redundant circuit and on-premise DC backbone | |

## 16. Logging, Observability, and Alerting

> **Goal:** Prove operations will see it when something breaks.

| Test ID | Check | Expected | Status |
|---|---|---|---|
| TC-16-001 | VPC Flow Logs enabled on all segment VPCs | Confirmed in log store | |
| TC-16-002 | Firewall logs forwarded to SIEM / central log store | Events present | |
| TC-16-003 | Network Manager events to CloudWatch | Events present | |
| TC-16-004 | Alarm: BGP neighbor down | Fires on test | |
| TC-16-005 | Alarm: DX connection down | Fires on test | |
| TC-16-006 | Alarm: CNE attachment state change | Fires on test | |
| TC-16-007 | Alarm: firewall CPU / memory thresholds | Fires on test | |
| TC-16-008 | Synthetic probes on critical paths | Running, alerting on failure | |
| TC-16-009 | Core Network Policy change notification | SNS / Chatbot / ticket fires | |

## 17. Policy and Change Safety

> **Goal:** Prove the Core Network Policy itself is managed safely.

| Test ID | Check | Expected | Status |
|---|---|---|---|
| TC-17-001 | Core Network Policy in version control | Repo + last commit identified | |
| TC-17-002 | Change review uses `describe-core-network-change-set` dry-run | Evidence attached to change record | |
| TC-17-003 | Rollback to prior policy version | Successful on non-impacting change | |
| TC-17-004 | IAM review: policy modification principals | Only approved principals have write access | |
