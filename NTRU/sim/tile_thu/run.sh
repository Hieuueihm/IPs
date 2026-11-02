#!/bin/sh
# Regression of the tile test block (spec 2.0, 11_kiem_thu_tile.md), acceptance RTL. Three modes since 02/11/2026:
# NTT (req_mode 0), FFT 32 / 64 / 128 bit (1), packed NTT with two 16-bit coefficients per word (2).
# Variants: 1 = current design, reduction on the multiplier array (NTT and packed NTT every 3 cycles);
# 3 = comparison design with dedicated Montgomery reduction (NTT every cycle; no packed NTT mode).
# Usage (from the project root): sh sim/tile_thu/run.sh [rtl files...]
#   VARIANTS="3" limits the run to the given variants (default: both).
#   IVFLAGS="-DTL_IN_REG=1" adds iverilog flags (RTL options); BUILD=<dir> changes the build folder.
#   default RTL: hdl/mul_ss.v hdl/tile/tile_thu.sv; the RTL must take the parameter TREN_MANG
#   and, for group C, the fault defines listed in tb_tile_thu.sv / tile_thu.sv.
# The FFT mode needs the beats of a 32-bit butterfly in consecutive datapath cycles, so it is only defined with
# EN_REG = 0 (spec 10, 4.7); with -DTL_EN_REG=1 its runs (and the mode-change chain, which includes it) are skipped.
# Every line ends in PASS or FAIL; the group C lines must say "bắt được".
set -e
A=spec/FlexTransform/2.0/assets/tile
B=${BUILD:-sim/tile_thu/build}
IVFLAGS=${IVFLAGS:-}
TB=sim/tile_thu/tb_tile_thu.sv
RTL=${*:-"hdl/mul_ss.v hdl/tile/tile_thu.sv"}
VARIANTS=${VARIANTS:-"3 1"}
M5=1
case "$IVFLAGS" in *TL_EN_REG=1*) M5=0 ;; esac
mkdir -p $B
for v in $VARIANTS; do iverilog -g2012 $IVFLAGS -P tb_tile_thu.TREN_MANG=$v -o $B/tb_$v.vvp $RTL $TB; done

run() { # binary label args...
    bin=$1; label=$2; shift 2
    out=$(vvp -n $bin "$@")
    echo "$label $* | $(echo "$out" | grep '^TOTAL')"
    [ -n "$VERBOSE" ] && echo "   $(echo "$out" | grep '^GROUP' | sed 's/.*mode=\([0-9]\) .* lat=\([0-9.]*\) rate=\([0-9.]*\)/m\1 lat \2 rate \3/' | sort -u | tr '\n' ';')"
    return 0
}
must_fail() { # binary label args...
    bin=$1; label=$2; shift 2
    if vvp -n $bin "$@" | grep -q '^TOTAL.*FAIL'; then r="bắt được"; else r="KHÔNG bắt được"; fi
    echo "$label $* | $r"
}

for v in $VARIANTS; do
    b=$B/tb_$v.vvp
    echo "== variant $v, nhóm A, B: số học, dừng chung, request thưa, ghi hằng số lúc bận, reset giữa chừng, lịch"
    FILES="ntt:0"
    [ $M5 = 1 ] && FILES="$FILES fft32bf:1 fftwbf:2"
    [ $v = 1 ] && FILES="$FILES ntt16:3"
    for f in $FILES; do
        set -- $(echo $f | tr ':' ' ')
        VERBOSE=1 run $b "variant=$v" +FILE=$A/$1.txt +KIND=$2
        run $b "variant=$v" +FILE=$A/$1.txt +KIND=$2 +STALL=10 +SEED=11
        run $b "variant=$v" +FILE=$A/$1.txt +KIND=$2 +STALL=30 +BURST=1 +SEED=12
        run $b "variant=$v" +FILE=$A/$1.txt +KIND=$2 +SPARSE=50 +SEED=13
        run $b "variant=$v" +FILE=$A/$1.txt +KIND=$2 +CFGBUSY=1 +SPARSE=30 +SEED=33
        run $b "variant=$v" +FILE=$A/$1.txt +KIND=$2 +RESETAT=5 +STALL=10 +SEED=34
        run $b "variant=$v" +FILE=$A/$1.txt +KIND=$2 +SCHED=1 +STALL=10 +SPARSE=20 +SEED=35
    done
    echo "== variant $v, tốc độ (nhóm ≥ 1 000 request, không dừng) và hai ô modulus"
    VERBOSE=1 run $b "variant=$v" +FILE=$A/ntt.txt +KIND=0 +REP=6
    run $b "variant=$v" +FILE=$A/ntt.txt +KIND=0 +MIX=1 +STALL=20 +BURST=1 +SPARSE=30 +SEED=32
    [ $M5 = 1 ] && VERBOSE=1 run $b "variant=$v" +FILE=$A/fft32bf.txt +KIND=1 +REP=2
    [ $M5 = 1 ] && VERBOSE=1 run $b "variant=$v" +FILE=$A/fftwbf.txt +KIND=2 +REP=2
    [ $v = 1 ] && VERBOSE=1 run $b "variant=$v" +FILE=$A/ntt16.txt +KIND=3 +REP=5
    [ $v = 1 ] && run $b "variant=$v" +FILE=$A/ntt16.txt +KIND=3 +MIX=1 +STALL=20 +BURST=1 +SPARSE=30 +SEED=43
    echo "== variant $v, nhóm B: đổi chế độ; nhóm C: testbench phải bắt được lỗi cài vào"
    if [ $v = 1 ] && [ $M5 = 1 ]; then
        run $b "variant=$v" +CHAIN=$A
        run $b "variant=$v" +CHAIN=$A +STALL=30 +BURST=1 +SPARSE=30 +SEED=21
        run $b "variant=$v" +CHAIN=$A +RESETAT=7 +SPARSE=30 +SEED=25
        must_fail $b "variant=$v sửa giá trị mong đợi" +CHAIN=$A +CORRUPT=1
        must_fail $b "variant=$v đổi chỗ hai kết quả" +CHAIN=$A +SWAPEXP=1
    else
        must_fail $b "variant=$v sửa giá trị mong đợi" +FILE=$A/ntt.txt +KIND=0 +CORRUPT=1
        must_fail $b "variant=$v đổi chỗ hai kết quả" +FILE=$A/ntt.txt +KIND=0 +SWAPEXP=1
    fi
    for fault in FAULT_NO_NZ FAULT_NZ_ONE FAULT_NO_SUBQ FAULT_HALVE_ALWAYS FAULT_SWAP_XY; do
        iverilog -g2012 $IVFLAGS -D$fault -P tb_tile_thu.TREN_MANG=$v -o $B/f_$v.vvp $RTL $TB
        must_fail $B/f_$v.vvp "variant=$v $fault" +FILE=$A/ntt.txt +KIND=0
        [ $v = 1 ] && must_fail $B/f_$v.vvp "variant=$v $fault NTT hai hệ số" +FILE=$A/ntt16.txt +KIND=3
    done
    if [ $M5 = 1 ]; then
        iverilog -g2012 $IVFLAGS -DFAULT_SWAP_XY -P tb_tile_thu.TREN_MANG=$v -o $B/f_$v.vvp $RTL $TB
        must_fail $B/f_$v.vvp "variant=$v FAULT_SWAP_XY FFT 32" +FILE=$A/fft32bf.txt +KIND=1
        must_fail $B/f_$v.vvp "variant=$v FAULT_SWAP_XY FFT 64/128" +FILE=$A/fftwbf.txt +KIND=2
        iverilog -g2012 $IVFLAGS -DFAULT_NO_CARRY -P tb_tile_thu.TREN_MANG=$v -o $B/f_$v.vvp $RTL $TB
        must_fail $B/f_$v.vvp "variant=$v FAULT_NO_CARRY" +FILE=$A/fftwbf.txt +KIND=2
    fi
    iverilog -g2012 $IVFLAGS -DFAULT_IGNORE_SLOT -P tb_tile_thu.TREN_MANG=$v -o $B/f_$v.vvp $RTL $TB
    must_fail $B/f_$v.vvp "variant=$v FAULT_IGNORE_SLOT" +FILE=$A/ntt.txt +KIND=0 +MIX=1
    [ $v = 1 ] && must_fail $B/f_$v.vvp "variant=$v FAULT_IGNORE_SLOT NTT hai hệ số" +FILE=$A/ntt16.txt +KIND=3 +MIX=1
done
exit 0
