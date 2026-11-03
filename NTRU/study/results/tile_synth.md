Yosys: `Yosys 0.70 (git sha1 28ba3cb92, Release, Clang /workspace/YoWASP/yosys/wasi-sdk-33.0-x86_64-linux/share/cmake/../..//bin/clang++ 22.1.0)`. Gate mapping `abc -g AND,NAND,OR,NOR,XOR,XNOR,ANDNOT,ORNOT,MUX`; GE weights are approximate (FF = 4.67 GE).

| Flow | Config | Comb GE | × u32 | FF | Total GE | Depth (cells) | × u32 |
|---|---|---:|---:|---:|---:|---:|---:|
| array | Baseline: unsigned 32x32 | 9374.3 | 1.0 | 128 | 9972.1 | 126 | 1.0 |
| array | L32 sign-select (CORR) | 10209.3 | 1.089 | 131 | 10821.1 | 127 | 1.008 |
| array | L32 via extension (= 33x33 signed) | 11105.6 | 1.185 | 131 | 11717.4 | 109 | 0.865 |
| array | 2x2 L16 sign-select, split only | 10738.4 | 1.146 | 268 | 11989.9 | 64 | 0.508 |
| array | 2x2 L16 sign-select, split + fuse | 11825.0 | 1.261 | 269 | 13081.2 | 127 | 1.008 |
| array | 2x2 L17 signed-only, split + fuse | 12962.3 | 1.383 | 269 | 14218.5 | 127 | 1.008 |
| booth | Baseline: unsigned 32x32 | 7683.5 | 1.0 | 128 | 8281.2 | 129 | 1.0 |
| booth | L32 sign-select (CORR) | 8280.0 | 1.078 | 131 | 8891.8 | 132 | 1.023 |
| booth | L32 via extension (= 33x33 signed) | 7992.1 | 1.04 | 131 | 8603.9 | 128 | 0.992 |
| booth | 2x2 L16 sign-select, split only | 9376.8 | 1.22 | 268 | 10628.4 | 68 | 0.527 |
| booth | 2x2 L16 sign-select, split + fuse | 10531.4 | 1.371 | 269 | 11787.6 | 135 | 1.047 |
| booth | 2x2 L17 signed-only, split + fuse | 10063.4 | 1.31 | 269 | 11319.7 | 136 | 1.054 |
