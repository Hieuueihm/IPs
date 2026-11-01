#!/bin/sh
# Regression of the tile test block (spec 2.0, 11_kiem_thu_tile.md), acceptance RTL, one 32-bit lane.
# Variants: 3 = architecture v1 (dedicated Montgomery, one NTT per cycle), 1 = reduction on the
# multiplier array (one NTT every 3 cycles; rejected by hypothesis 2, kept to compare).
# Usage (from the project root): sh sim/tile_thu/run.sh [rtl files...]
#   VARIANTS="3" limits the run to the given variants (default: both).
#   IVFLAGS="-DTL_IN_REG=1" adds iverilog flags (RTL options); BUILD=<dir> changes the build folder.
#   default RTL: hdl/mul_ss.v hdl/tile/tile_thu.sv; the RTL must take the parameter TREN_MANG
#   and, for group C, the fault defines listed in tb_tile_thu.sv / tile_thu.sv.
# The draft in hdl/tile_thu/ keeps the two-lane contract (cfg_lane32) and runs only with the
# testbench saved in docs/plan_history/before_one_lane_2026-10-31/sim/.
# Every line ends in PASS or FAIL; the group C lines must say "bắt được".
set -e
A=spec/FlexTransform/2.0/assets/tile
# Mode 5 (FFT butterfly) needs its two beats in consecutive datapath cycles, so it is only defined with EN_REG = 0
# (spec 10, 4.7); with -DTL_EN_REG=1 its runs are skipped.
M5=1
case "$IVFLAGS" in *TL_EN_REG=1*) M5=0 ;; esac
B=${BUILD:-sim/tile_thu/build}
IVFLAGS=${IVFLAGS:-}
TB=sim/tile_thu/tb_tile_thu.sv
RTL=${*:-"hdl/mul_ss.v hdl/tile/tile_thu.sv"}
VARIANTS=${VARIANTS:-"3 1"}
mkdir -p $B
for v in $VARIANTS; do
    iverilog -g2012 $IVFLAGS -P tb_tile_thu.TREN_MANG=$v -o $B/tb_$v.vvp $RTL $TB
done

run() { # binary label args...
    bin=$1; label=$2; shift 2
    out=$(vvp -n $bin "$@")
    tot=$(echo "$out" | grep '^TOTAL')
    echo "$label $* | $tot"
    [ -n "$VERBOSE" ] && echo "   $(echo "$out" | grep '^GROUP' | sed 's/.*mode=\([0-9]\) .* lat=\([0-9.]*\) rate=\([0-9.]*\)/m\1 lat \2 rate \3/' | sort -u | tr '\n' ';')"
    return 0
}
must_fail() { # binary label args...
    bin=$1; label=$2; shift 2
    if vvp -n $bin "$@" | grep -q '^TOTAL.*FAIL'; then r="bắt được"; else r="KHÔNG bắt được"; fi
    echo "$label $* | $r"
}

echo "== Nhóm A, B: số học, dừng chung, request thưa, tốc độ"
for v in $VARIANTS; do
    FILES="raw32:0 fft32:1 ntt:2"
    [ $M5 = 1 ] && FILES="$FILES fft32bf:3"
    for f in $FILES; do
        f=$(echo $f | tr ':' ' ')
        set -- $f
        VERBOSE=1 run $B/tb_$v.vvp "variant=$v" +FILE=$A/$1.txt +KIND=$2
        run $B/tb_$v.vvp "variant=$v" +FILE=$A/$1.txt +KIND=$2 +STALL=10 +SEED=11
        run $B/tb_$v.vvp "variant=$v" +FILE=$A/$1.txt +KIND=$2 +STALL=30 +BURST=1 +SEED=12
        run $B/tb_$v.vvp "variant=$v" +FILE=$A/$1.txt +KIND=$2 +SPARSE=50 +SEED=13
    done
    run $B/tb_$v.vvp "variant=$v" +FILE=$A/ntt.txt +STALL=30 +BURST=1 +SPARSE=50 +SEED=14
    # rate check: groups of at least 1000 requests with no stall (tb compares with spec 10 section 6)
    VERBOSE=1 run $B/tb_$v.vvp "variant=$v" +FILE=$A/raw32.txt +KIND=0 +REP=2
    VERBOSE=1 run $B/tb_$v.vvp "variant=$v" +FILE=$A/fft32.txt +KIND=1 +REP=2
    VERBOSE=1 run $B/tb_$v.vvp "variant=$v" +FILE=$A/ntt.txt +REP=6
    [ $M5 = 1 ] && VERBOSE=1 run $B/tb_$v.vvp "variant=$v" +FILE=$A/fft32bf.txt +KIND=3 +REP=2
done

echo "== Nhóm B: đổi chế độ, ghi hằng số lúc bận, reset giữa chừng, lịch không phụ thuộc dữ liệu, trộn hai modulus"
for v in $VARIANTS; do
    b=$B/tb_$v.vvp
    run $b "variant=$v" +CHAIN=$A
    run $b "variant=$v" +CHAIN=$A +STALL=30 +BURST=1 +SPARSE=30 +SEED=21
    run $b "variant=$v" +CHAIN=$A +CFGBUSY=1 +STALL=20 +SPARSE=30 +SEED=22
    run $b "variant=$v" +FILE=$A/ntt.txt +CFGBUSY=1 +SPARSE=30 +SEED=24
    run $b "variant=$v" +CHAIN=$A +RESETAT=7 +SPARSE=30 +SEED=25
    run $b "variant=$v" +FILE=$A/ntt.txt +RESETAT=3 +STALL=10 +SEED=26
    run $b "variant=$v" +CHAIN=$A +SCHED=1 +STALL=20 +SPARSE=30 +SEED=27
    run $b "variant=$v" +FILE=$A/ntt.txt +SCHED=1 +STALL=10 +SPARSE=20 +SEED=29
    run $b "variant=$v" +FILE=$A/ntt.txt +MIX=1 +STALL=20 +BURST=1 +SPARSE=30 +SEED=32
    [ $M5 = 1 ] && run $b "variant=$v" +FILE=$A/fft32bf.txt +KIND=3 +CFGBUSY=1 +SPARSE=30 +SEED=33
    [ $M5 = 1 ] && run $b "variant=$v" +FILE=$A/fft32bf.txt +KIND=3 +RESETAT=5 +STALL=10 +SEED=34
    [ $M5 = 1 ] && run $b "variant=$v" +FILE=$A/fft32bf.txt +KIND=3 +SCHED=1 +STALL=10 +SPARSE=20 +SEED=35
done

echo "== Nhóm C: testbench phải bắt được lỗi cài vào"
for v in $VARIANTS; do
    b=$B/tb_$v.vvp
    must_fail $b "variant=$v sửa giá trị mong đợi" +CHAIN=$A +CORRUPT=1
    must_fail $b "variant=$v đổi chỗ hai kết quả" +CHAIN=$A +SWAPEXP=1
    for fault in FAULT_NO_NZ FAULT_NZ_ONE FAULT_NO_SUBQ FAULT_HALVE_ALWAYS FAULT_SWAP_XY; do
        iverilog -g2012 $IVFLAGS -D$fault -P tb_tile_thu.TREN_MANG=$v -o $B/f_$v.vvp $RTL $TB
        must_fail $B/f_$v.vvp "variant=$v $fault" +FILE=$A/ntt.txt
    done
    if [ $M5 = 1 ]; then
        iverilog -g2012 $IVFLAGS -DFAULT_SWAP_XY -P tb_tile_thu.TREN_MANG=$v -o $B/f_$v.vvp $RTL $TB
        must_fail $B/f_$v.vvp "variant=$v FAULT_SWAP_XY mode 5" +FILE=$A/fft32bf.txt +KIND=3
    fi
    iverilog -g2012 $IVFLAGS -DFAULT_IGNORE_SLOT -P tb_tile_thu.TREN_MANG=$v -o $B/f_$v.vvp $RTL $TB
    must_fail $B/f_$v.vvp "variant=$v FAULT_IGNORE_SLOT" +FILE=$A/ntt.txt +MIX=1
done
