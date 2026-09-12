# traffic_light dangling branch repair

The customer screenshot of N007 contains a horizontal wire whose left end is
unconnected. The original file is protected as tests/fixtures/traffic_light-dangling.ldr
with SHA-256 5a92767855621bb322b6c2f4dff798c433510e586fb05bca9f2e4b66305cf7aa.

The first fix only handled N007 and was insufficient. The replacement policy
applies to EVERY generated expression: nested series/parallel joins (`E200` and
`E443`) are eliminated by computing subexpressions in flat helper-M networks
immediately before their original consumer. Boolean OPEN constants are replaced
by wired contradictions. The sampled inverted counter CLR rail remains intact.

N007 still implements the following four logical paths, now via helper networks:

1. X0 AND M11 AND NOT T1
2. X0 AND M10 AND T0
3. X0 AND M10 AND X1
4. X0 AND NOT M10 AND NOT M11 AND NOT M12 AND X1

All 128 truth-table combinations match the original expression. Whole-program
scan-model regression checks 256 seeded input scans and compares every original
device value. Original N006, N007 and N008 are all lowered, not just N007.
The program expands from 12 to 25 networks. Header/footer remain unchanged.
Helper devices are M3..M9 and M13..M18 (13 devices); none occur in the original
file. They must also be reserved if importing into a larger project. The output
response contains source-to-generated network mapping and allocated helpers.

The normalization applies to all creation tools and inserted/replaced networks,
including timer inputs and counter input polarity. Expansions are bounded and
oversized expressions or exhausted helper memory are rejected before writing.
All 11 control recipes and the maximum 16-step sequence are regression-tested
for absence of nested joins and equivalent original-device scan-model results.
All 13 example artifacts were regenerated under the `connected_` prefix.
Forensic read/export intentionally remain lossless, including the original
problematic bytes; they do not silently repair an existing file.

Use C:\VM_Share\artifacts\traffic_light_connected.ldr instead of the earlier
traffic_light_fixed.ldr. The original and previous candidates were not overwritten.
The user subsequently confirmed successful import of this connected artifact
(SHA-256 a4694aa8db73737ada925742ebc6ba164aee52e56137bd5ae201017c203b3b94).
An exact copy is protected as tests/fixtures/traffic_light-connected-verified.ldr.
This is user-reported evidence for these exact bytes, not PLC commissioning or
blanket verification of later optimized files. See logic-optimization.md.
