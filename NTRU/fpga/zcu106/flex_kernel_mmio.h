#ifndef FLEX_KERNEL_MMIO_H
#define FLEX_KERNEL_MMIO_H
#include <stdint.h>
#include <stddef.h>

/* Map device registers as device/uncached memory. The generated BD uses
 * 0xA0000000; pass the actual exported address to these functions. */
typedef struct { uint32_t limb[4]; } flex_word;
enum flex_op { FLEX_FFT, FLEX_IFFT, FLEX_CMUL, FLEX_SPLIT, FLEX_MERGE,
               FLEX_NTT, FLEX_INTT, FLEX_TOMONT, FLEX_MODMUL };
enum { FLEX_OK=0, FLEX_TIMEOUT=-1, FLEX_HW_ERROR=-2, FLEX_BAD_STATE=-3 };

static inline void flex_barrier(void) {
#if defined(__aarch64__) || defined(__arm__)
    __asm__ volatile("dmb sy" ::: "memory");
#elif defined(__GNUC__)
    __asm__ volatile("" ::: "memory");
#endif
}
static inline void flex_wr(volatile uint32_t *base, unsigned offset, uint32_t v) {
    flex_barrier();base[offset/4]=v;flex_barrier();
}
static inline uint32_t flex_rd(volatile uint32_t *base,unsigned offset) {
    uint32_t v;flex_barrier();v=base[offset/4];flex_barrier();return v;
}
static inline int flex_configure(volatile uint32_t *base,enum flex_op op,
                                 unsigned logn,unsigned width,unsigned profile) {
    if(op>FLEX_MODMUL||logn>10||width>2||profile>1)return FLEX_BAD_STATE;
    if(!(flex_rd(base,8)&1))return FLEX_BAD_STATE;
    flex_wr(base,0,(unsigned)op|(logn<<4)|(width<<8)|(profile<<10));return FLEX_OK;
}
static inline int flex_load(volatile uint32_t *base,unsigned store,unsigned index,const flex_word *v) {
    unsigned i;if(store>1||index>1023||!(flex_rd(base,8)&2))return FLEX_BAD_STATE;
    flex_wr(base,0x10,index);flex_wr(base,0x14,store);
    for(i=0;i<4;i++)flex_wr(base,0x20+4*i,v->limb[i]);
    flex_wr(base,0x18,1);return FLEX_OK;
}
static inline int flex_start(volatile uint32_t *base) {
    if(!(flex_rd(base,8)&1))return FLEX_BAD_STATE;
    flex_wr(base,4,1);return FLEX_OK;
}
static inline int flex_wait(volatile uint32_t *base,unsigned timeout) {
    while(timeout--) {uint32_t s=flex_rd(base,8);if(s&4)return (s&8)?FLEX_HW_ERROR:FLEX_OK;}
    return FLEX_TIMEOUT;
}
static inline int flex_read(volatile uint32_t *base,unsigned index,flex_word *v,unsigned timeout) {
    unsigned i;if(index>1023||!(flex_rd(base,8)&4))return FLEX_BAD_STATE;
    flex_wr(base,0x10,index);flex_wr(base,0x18,2);
    while(!(flex_rd(base,8)&16))if(!timeout--)return FLEX_TIMEOUT;
    for(i=0;i<4;i++)v->limb[i]=flex_rd(base,0x30+4*i);
    return FLEX_OK;
}
static inline int flex_ack(volatile uint32_t *base) {
    if(!(flex_rd(base,8)&4)||(flex_rd(base,4)&256))return FLEX_BAD_STATE;
    flex_wr(base,4,2);return FLEX_OK;
}
static inline void flex_reset(volatile uint32_t *base) {flex_wr(base,4,4);}
#endif
