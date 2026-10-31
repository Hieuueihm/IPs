# 05 — Requirements and verification traceability

Generated from [requirements.json](requirements.json). SHALL/MUST are mandatory.
Test definitions: [04](04_verification_acceptance.md). No RTL test is marked PASS by this table.

| Requirement | Mandatory behavior | Source | Tests |
|---|---|---|---|
| FT-SCP-001 | Implement opcodes 0..8 and reject reserved opcodes. | [00](00_scope_profiles.md) | T_CFG, T_FP_KERNEL, T_NTT_KERNEL |
| FT-SCP-002 | Enforce FFT formats 0..2 and RES16 format3 for NTT family. | [00](00_scope_profiles.md) | T_CFG |
| FT-SCP-003 | W128 is bit-exact to pinned scalar LP64 R8 numeric contract. | [00](00_scope_profiles.md) | T_FP_KERNEL, T_SIGNER |
| FT-SCP-004 | Do not lower precision automatically; W32/64 have only their explicit integer contract. | [00](00_scope_profiles.md) | T_CFG, T_FP_PRIM |
| FT-SCP-005 | Enforce the N/profile support table including incomplete q3329 N256. | [00](00_scope_profiles.md) | T_CFG, T_NTT_KERNEL |
| FT-SCP-006 | Enforce jobs limits; FFT jobs1 and NTT N8/16/32 limits8/4/2. | [00](00_scope_profiles.md) | T_CFG, T_JOBS |
| FT-SCP-007 | All jobs in a batch share op,fmt,profile,N and direction. | [00](00_scope_profiles.md) | T_CFG, T_JOBS |
| FT-SCP-008 | Keep every batched polynomial and job identity independent. | [00](00_scope_profiles.md) | T_JOBS, T_CONTEXT |
| FT-SCP-009 | Host owns load/read only in the states defined by protocol; no host requests in RUN. | [00](00_scope_profiles.md) | T_NATIVE, T_MEMORY |
| FT-SCP-010 | Issue/address/root/control schedules are independent of coefficient values for identical control state, address footprint and flow trace. | [00](00_scope_profiles.md) | T_PROFILE |
| FT-SCP-011 | Do not depend on unwritten RAM; reset does not implicitly initialize or zeroize data. | [00](00_scope_profiles.md) | T_RESET, T_MEMORY |
| FT-NUM-001 | Use W32/64/128 with fractional bits W/2. | [01](01_numeric_kernels.md) | T_FP_PRIM |
| FT-NUM-002 | Add/sub wrap modulo2^W without saturation. | [01](01_numeric_kernels.md) | T_FP_PRIM |
| FT-NUM-003 | Multiply with full mathematical product, bias2^(F-1), shiftF, then wrapW. | [01](01_numeric_kernels.md) | T_FP_PRIM, T_MUTATE |
| FT-NUM-004 | div2e wraps bias addition before arithmetic shift; shift0 is identity. | [01](01_numeric_kernels.md) | T_FP_PRIM |
| FT-NUM-005 | Use exact 3M with wrapped pre-add and independent per-real-product rounding. | [01](01_numeric_kernels.md) | T_FP_PRIM, T_FP_KERNEL |
| FT-NUM-006 | Lower limbs are unsigned; only each operand top limb is signed; preserve raw product sign. | [01](01_numeric_kernels.md) | T_FP_PRIM, T_ARRAY |
| FT-NUM-007 | Preserve retained W+F product bits, required carries and one final rounding; discard only exact zero-weight terms. | [01](01_numeric_kernels.md) | T_FP_PRIM, T_ARRAY |
| FT-NUM-008 | Use pinned exact FFT ROM bits, no sin/cos regeneration. | [01](01_numeric_kernels.md) | T_ROOT |
| FT-NUM-009 | Conjugate in128 before low-width quantization; form root sum after quantization. | [01](01_numeric_kernels.md) | T_ROOT, T_FP_KERNEL |
| FT-NUM-010 | Require canonical NTT coefficients/roots/results; no lazy/signed residue contract. | [01](01_numeric_kernels.md) | T_NTT_PRIM, T_NTT_KERNEL |
| FT-NUM-011 | Montgomery implements full unsigned T, m, carry and canonical conditional subtraction. | [01](01_numeric_kernels.md) | T_NTT_PRIM |
| FT-NUM-012 | Do not apply FFT product truncation to Montgomery T. | [01](01_numeric_kernels.md) | T_NTT_PRIM, T_ARRAY |
| FT-NUM-013 | Implement CT and GS component/domain equations exactly. | [01](01_numeric_kernels.md) | T_NTT_KERNEL, T_ARRAY |
| FT-NUM-014 | Root tables encode ordinary root times R; inverse ordinary roots before encoding. | [01](01_numeric_kernels.md) | T_ROOT, T_NTT_KERNEL |
| FT-KER-001 | FFT uses exact split-real/imag indexing, roots and wrapped arithmetic of section01.4. | [01](01_numeric_kernels.md) | T_FP_KERNEL |
| FT-KER-002 | IFFT uses inverse roots and final div2e(logn-1), including N1/N2 identity. | [01](01_numeric_kernels.md) | T_FP_KERNEL |
| FT-KER-003 | CMUL is pointwise complex3M, writes A and preserves B/C. | [01](01_numeric_kernels.md) | T_FP_KERNEL |
| FT-KER-004 | SPLIT preserves input stores and writes concatenated f0/f1 to C including N2 case. | [01](01_numeric_kernels.md) | T_FP_KERNEL |
| FT-KER-005 | MERGE reads half-length A/B and writes interleaved component C including N2 case. | [01](01_numeric_kernels.md) | T_FP_KERNEL |
| FT-KER-006 | NTT uses prescribed CT loop/root/output order and q3329 incomplete stop. | [01](01_numeric_kernels.md) | T_NTT_KERNEL |
| FT-KER-007 | INTT uses prescribed inverse GS loop and final inverse2^L normalization. | [01](01_numeric_kernels.md) | T_NTT_KERNEL |
| FT-KER-008 | TOMONT returns xR modq. | [01](01_numeric_kernels.md) | T_NTT_KERNEL |
| FT-KER-009 | MODMUL returns abR^-1 modq; no implicit ordinary multiply or BASEMUL. | [01](01_numeric_kernels.md) | T_NTT_KERNEL |
| FT-KER-010 | Paired/tail/scalar NTT tile modes preserve coefficient order, roots and job schedule. | [01](01_numeric_kernels.md) | T_ARRAY, T_NTT_KERNEL |
| FT-IF-001 | Transfer only on sampled rising edge valid&&ready. | [02](02_interfaces_protocol.md) | T_NATIVE, T_STABILITY |
| FT-IF-002 | Hold valid and complete payload until handshake except reset/canceled internal epoch. | [02](02_interfaces_protocol.md) | T_STABILITY, T_FLUSH |
| FT-IF-003 | Avoid combinational valid/ready loops. | [02](02_interfaces_protocol.md) | T_STABILITY, T_RELEASE |
| FT-IF-004 | Latch every CMD field on acceptance; later input changes have no effect. | [02](02_interfaces_protocol.md) | T_NATIVE |
| FT-IF-005 | Allow one outstanding CMD; host memory wins simultaneous IDLE arbitration. | [02](02_interfaces_protocol.md) | T_NATIVE |
| FT-IF-006 | Return exactly one tagged completion per accepted command except reset. | [02](02_interfaces_protocol.md) | T_NATIVE, T_RESET, T_FLUSH |
| FT-IF-007 | Publish OK only after all writes commit and command pipeline/context drain. | [02](02_interfaces_protocol.md) | T_NATIVE, T_CONTEXT |
| FT-IF-008 | Published completion is immutable through pause/flush until ACK; reset may cancel. | [02](02_interfaces_protocol.md) | T_STABILITY, T_FLUSH |
| FT-IF-009 | Internal packets retain sufficient epoch/context/lane/phase identity to retire correctly. | [03](03_microarchitecture_memory.md) | T_CONTEXT, T_ARRAY |
| FT-IF-010 | Use defined packet packing; zero reserved/inactive bits and preserve active lane masks. | [03](03_microarchitecture_memory.md) | T_ARRAY, T_CONTEXT |
| FT-RST-001 | Synchronous active-low reset clears all control valids/state and suppresses writes/replies; hold >=2edges. | [02](02_interfaces_protocol.md) | T_RESET |
| FT-RST-002 | Reset preserves data/ROM content; do not rely on initial for control reset. | [02](02_interfaces_protocol.md) | T_RESET, T_MEMORY |
| FT-ERR-001 | Validate command fields in specified error priority, without evaluating dependent invalid fields. | [02](02_interfaces_protocol.md) | T_CFG |
| FT-ERR-002 | Invalid CMD returns error/tag/mask0 without arithmetic/data/root issue or RAM change. | [02](02_interfaces_protocol.md) | T_CFG |
| FT-ERR-003 | Detected internal invariant failure stops command side effects, drains and returns INTERNAL_FAULT unless reset/flush takes priority. | [02](02_interfaces_protocol.md) | T_CONTEXT, T_FLUSH |
| FT-MEM-001 | Validate host store/alignment/range/state using specified priority. | [02](02_interfaces_protocol.md) | T_MEMORY |
| FT-MEM-002 | Implement byte-enable writes and little-endian raw128 lines; zero-strobe write is ACKed no-op. | [02](02_interfaces_protocol.md) | T_MEMORY |
| FT-MEM-003 | One outstanding host request, exactly one stable ordered response. | [02](02_interfaces_protocol.md) | T_MEMORY, T_STABILITY |
| FT-MEM-004 | ACK host write OK only after enabled bytes have committed. | [02](02_interfaces_protocol.md) | T_MEMORY |
| FT-MEM-005 | Enforce IDLE/RUN/DONE/FLUSH memory ownership and DONE write STATE behavior. | [02](02_interfaces_protocol.md) | T_MEMORY, T_NATIVE |
| FT-MEM-006 | Block new command until completion ACK and any earlier memory response drains. | [02](02_interfaces_protocol.md) | T_NATIVE |
| FT-MEM-007 | Apply fixed bijective bank/row mapping and <=1R+1W per bank per edge. | [03](03_microarchitecture_memory.md) | T_BANK |
| FT-MEM-008 | Bank read adapter latency is >=1 edge and held response cannot be overwritten. | [03](03_microarchitecture_memory.md) | T_BANK, T_STABILITY |
| FT-MEM-009 | Serialize overlapping read/write; never depend on macro read-during-write behavior. | [03](03_microarchitecture_memory.md) | T_BANK |
| FT-MEM-010 | Map FFT components to consecutive little-endian limbs16 and preserve split-real/imag layout. | [03](03_microarchitecture_memory.md) | T_MEMORY, T_FP_KERNEL |
| FT-MEM-011 | Map NTT job j coefficient i at word j*N+i, same map in B for MODMUL. | [03](03_microarchitecture_memory.md) | T_JOBS, T_MEMORY |
| FT-MEM-012 | Only bytes in output footprint may change; preserve all other bytes/stores. | [03](03_microarchitecture_memory.md) | T_JOBS, T_MEMORY, T_FP_KERNEL |
| FT-CTL-001 | Pause holds datapath/issue/context/command writes while published external responses may ACK. | [02](02_interfaces_protocol.md) | T_STABILITY, T_CONTEXT, T_PERF |
| FT-CTL-002 | Reset/flush override pause and can drain/cancel without pause deadlock. | [02](02_interfaces_protocol.md) | T_RESET, T_FLUSH |
| FT-FLS-001 | Implement four-phase level flush handshake and block new requests through release. | [02](02_interfaces_protocol.md) | T_FLUSH |
| FT-FLS-002 | Suppress command writes from first sampled flush edge, drain/invalidate all canceled packets. | [02](02_interfaces_protocol.md) | T_FLUSH, T_CONTEXT |
| FT-FLS-003 | Unpublished command gets exactly one ABORTED mask0; no rollback, all batch outputs invalid. | [02](02_interfaces_protocol.md) | T_FLUSH |
| FT-FLS-004 | Preserve published completion unchanged and do not wait for cpl_ready to ACK flush. | [02](02_interfaces_protocol.md) | T_FLUSH |
| FT-FLS-005 | IDLE flush produces no completion; reset cancels flush/control without reply. | [02](02_interfaces_protocol.md) | T_FLUSH, T_RESET |
| FT-FLS-006 | Flush completes <=256 clocks after accepted host responses drain regardless of pause/completion backpressure. | [02](02_interfaces_protocol.md) | T_FLUSH |
| FT-ARC-001 | Shared array sustains legal input frame II1 with ready consumer and no pause/flush. | [03](03_microarchitecture_memory.md) | T_ARRAY, T_PERF |
| FT-ARC-002 | Publish per-mode latency; hold output and identity through backpressure. | [03](03_microarchitecture_memory.md) | T_ARRAY, T_STABILITY |
| FT-ARC-003 | Align bypass/tail data, roots, valid and metadata. | [03](03_microarchitecture_memory.md) | T_ARRAY |
| FT-ARC-004 | Service bank conflicts in legal rounds and gather every word into its correct operand slot. | [03](03_microarchitecture_memory.md) | T_BANK, T_FP_KERNEL |
| FT-ARC-005 | Budget FFT root1/cycle, prefetch complete lane roots, clear cache valid at each CMD/flush. | [03](03_microarchitecture_memory.md) | T_ROOT, T_PROFILE |
| FT-ARC-006 | Pack small independent NTT jobs with per-job index/root schedule and active masks. | [03](03_microarchitecture_memory.md) | T_JOBS, T_ARRAY |
| FT-ARC-007 | Use specified NTT bundle order/bank mapping, broadcast or serialize conflicts, no padded-row request. | [03](03_microarchitecture_memory.md) | T_ROOT, T_BANK |
| FT-ARC-008 | Preserve limb fusion grouping/sign/shift and retained-width exact product. | [03](03_microarchitecture_memory.md) | T_ARRAY, T_FP_PRIM |
| FT-ARC-009 | Keep FFT half-operands/cross products and NTT A/sum/root/tail side paths until consumed. | [03](03_microarchitecture_memory.md) | T_ARRAY, T_CONTEXT |
| FT-ARC-010 | Provide implementation manifest covering all items in03.9 and interface mapping. | [03](03_microarchitecture_memory.md) | T_RELEASE |
| FT-CTX-001 | Use two independently owned microbatch contexts; no reuse until all effects commit. | [03](03_microarchitecture_memory.md) | T_CONTEXT |
| FT-CTX-002 | Collect p0/p1/p2 by logical lane; never combine incomplete or mismatched triplets. | [03](03_microarchitecture_memory.md) | T_CONTEXT |
| FT-CTX-003 | Maintain command tag, job, stage, lane, destination and epoch ownership through retire. | [03](03_microarchitecture_memory.md) | T_CONTEXT |
| FT-CTX-004 | Detect duplicate/unknown current-epoch phase errors; discard canceled-epoch packets without new-command writes. | [03](03_microarchitecture_memory.md) | T_CONTEXT |
| FT-CTX-005 | READY requires all coefficients/roots and output capacity for active lanes. | [03](03_microarchitecture_memory.md) | T_CONTEXT, T_ROOT |
| FT-CTX-006 | Inactive lanes are explicitly masked/zero and have no side effect. | [03](03_microarchitecture_memory.md) | T_CONTEXT, T_ARRAY |
| FT-CTX-007 | Memory-pass barrier waits for committed writes; paired NTT layers fuse inside one pass; resolve in-place RAW/WAW hazards. | [03](03_microarchitecture_memory.md) | T_CONTEXT, T_BANK |
| FT-CTX-008 | Epoch increments on CMD/cancel; modulo wrap never replaces drain; reset clears every pipeline valid. | [03](03_microarchitecture_memory.md) | T_CONTEXT, T_RESET, T_FLUSH |
| FT-DV-001 | Map every mandatory requirement to recorded test results or explicitly reviewed waiver; NOT_RUN is not PASS. | [04](04_verification_acceptance.md) | T_RELEASE |
| FT-DV-002 | Check coefficient-independent schedule with identical config/initial state/flow trace. | [04](04_verification_acceptance.md) | T_PROFILE |
| FT-DV-003 | Publish completion <=1048576 active clocks for a valid unflushed/unreset command. | [04](04_verification_acceptance.md) | T_STRESS, T_PERF |
| FT-DV-004 | Release source/tool/seed/hash/coverage/assertion/provenance/performance/deviation manifest. | [04](04_verification_acceptance.md) | T_RELEASE |
