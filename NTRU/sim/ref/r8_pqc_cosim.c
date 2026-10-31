/* Deterministic capture/replay at the live C application boundary.
 * Replay never calls the replaced C kernels, and checks every live input.
 */
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "inner.h"
#include "falcon.h"
#include "r8_pqc_bridge.h"

#if !FALCON_FXP || FALCON_AVX2
#error scalar Q64.64 is required
#endif

void r8_original_FFT(fpr *, unsigned);
void r8_original_iFFT(fpr *, unsigned);
void r8_original_poly_mul_fft(fpr *, const fpr *, unsigned);
void r8_original_poly_split_fft(fpr *, fpr *, const fpr *, unsigned);
void r8_original_poly_merge_fft(fpr *, const fpr *, const fpr *, unsigned);
static FILE *replacement;
static const char *origin="init";
static unsigned long long sequence;
static const char *artifact_dir;

static void fail(const char *reason)
{
    fprintf(stderr,"BRIDGE_FAIL sequence=%llu origin=%s reason=%s\n",sequence,origin,reason);
    exit(7);
}
static void *alloc_bytes(size_t n)
{
    void *p=calloc(1,n);if(!p)fail("allocation");return p;
}
static void dump_fpr(const fpr *a,size_t n)
{
    putchar('[');
    for(size_t i=0;i<n;i++)printf("%s\"%016" PRIx64 "%016" PRIx64 "\"",i?",":"",(uint64_t)(a[i].v>>64),(uint64_t)a[i].v);
    putchar(']');
}
static void dump_mod(const uint16_t *a,size_t n)
{
    putchar('[');for(size_t i=0;i<n;i++)printf("%s%u",i?",":"",a[i]);putchar(']');
}
static fpr read_fpr(void)
{
    char s[40],*end;fpr a;
    if(fscanf(replacement,"%39s",s)!=1||strlen(s)!=32)fail("fpr word");
    uint64_t lo=strtoull(s+16,&end,16);if(*end)fail("fpr low");
    s[16]=0;uint64_t hi=strtoull(s,&end,16);if(*end)fail("fpr high");
    a.v=((uint128_t)hi<<64)|lo;return a;
}
static uint16_t read_mod(void)
{
    unsigned x;if(fscanf(replacement,"%u",&x)!=1||x>=12289)fail("mod word");return (uint16_t)x;
}
static void read_header(const char *op,unsigned logn,size_t na,size_t nb,size_t ny,size_t nz)
{
    char name[24];unsigned l;size_t aa,bb,yy,zz;
    if(fscanf(replacement,"%23s %u %zu %zu %zu %zu",name,&l,&aa,&bb,&yy,&zz)!=6)fail("record missing");
    if(strcmp(name,op)||l!=logn||aa!=na||bb!=nb||yy!=ny||zz!=nz)fail("record metadata");
}
static int replay_fpr(const char *op,unsigned logn,const fpr *a,size_t na,const fpr *b,size_t nb,fpr *y,size_t ny,fpr *z,size_t nz)
{
    if(!replacement)return 0;
    read_header(op,logn,na,nb,ny,nz);
    for(size_t i=0;i<na;i++)if(read_fpr().v!=a[i].v)fail("live FFT input a");
    for(size_t i=0;i<nb;i++)if(read_fpr().v!=b[i].v)fail("live FFT input b");
    for(size_t i=0;i<ny;i++)y[i]=read_fpr();
    for(size_t i=0;i<nz;i++)z[i]=read_fpr();
    sequence++;return 1;
}
static fpr *snapshot(const fpr *a,size_t n)
{
    fpr *p=alloc_bytes(n*sizeof *p);memcpy(p,a,n*sizeof *p);return p;
}
static void emit_fpr(const char *op,unsigned logn,const fpr *a,size_t na,const fpr *b,size_t nb,const fpr *y,size_t ny,const fpr *z,size_t nz)
{
    printf("{\"type\":\"kernel\",\"id\":%llu,\"origin\":\"%s\",\"op\":\"%s\",\"logn\":%u,\"a\":",sequence++,origin,op,logn);
    dump_fpr(a,na);if(nb){printf(",\"b\":");dump_fpr(b,nb);}printf(",\"out\":");dump_fpr(y,ny);
    if(nz){printf(",\"out1\":");dump_fpr(z,nz);}puts("}");
}
void Zf(FFT)(fpr *a,unsigned l)
{
    size_t n=(size_t)1<<l;if(replay_fpr("FFT",l,a,n,NULL,0,a,n,NULL,0))return;
    fpr *before=snapshot(a,n);r8_original_FFT(a,l);emit_fpr("FFT",l,before,n,NULL,0,a,n,NULL,0);free(before);
}
void Zf(iFFT)(fpr *a,unsigned l)
{
    size_t n=(size_t)1<<l;if(replay_fpr("IFFT",l,a,n,NULL,0,a,n,NULL,0))return;
    fpr *before=snapshot(a,n);r8_original_iFFT(a,l);emit_fpr("IFFT",l,before,n,NULL,0,a,n,NULL,0);free(before);
}
void Zf(poly_mul_fft)(fpr *a,const fpr *b,unsigned l)
{
    size_t n=(size_t)1<<l;if(replay_fpr("CMUL",l,a,n,b,n,a,n,NULL,0))return;
    fpr *before=snapshot(a,n);r8_original_poly_mul_fft(a,b,l);emit_fpr("CMUL",l,before,n,b,n,a,n,NULL,0);free(before);
}
void Zf(poly_split_fft)(fpr *y,fpr *z,const fpr *a,unsigned l)
{
    size_t n=(size_t)1<<l;if(replay_fpr("SPLIT",l,a,n,NULL,0,y,n/2,z,n/2))return;
    fpr *before=snapshot(a,n);r8_original_poly_split_fft(y,z,a,l);
    emit_fpr("SPLIT",l,before,n,NULL,0,y,n/2,z,n/2);free(before);
}
void Zf(poly_merge_fft)(fpr *y,const fpr *a,const fpr *b,unsigned l)
{
    size_t n=(size_t)1<<l;if(replay_fpr("MERGE",l,a,n/2,b,n/2,y,n,NULL,0))return;
    fpr *aa=snapshot(a,n/2),*bb=snapshot(b,n/2);r8_original_poly_merge_fft(y,a,b,l);
    emit_fpr("MERGE",l,aa,n/2,bb,n/2,y,n,NULL,0);free(aa);free(bb);
}
int pqc_ntt_replay(const char *op,uint16_t *a,const uint16_t *b,unsigned l)
{
    if(!replacement)return 0;
    size_t n=(size_t)1<<l;read_header(op,l,n,b?n:0,n,0);
    for(size_t i=0;i<n;i++)if(read_mod()!=a[i])fail("live NTT input a");
    if(b)for(size_t i=0;i<n;i++)if(read_mod()!=b[i])fail("live NTT input b");
    for(size_t i=0;i<n;i++)a[i]=read_mod();sequence++;return 1;
}
void pqc_ntt_emit(const char *op,const uint16_t *a,const uint16_t *b,const uint16_t *y,unsigned l)
{
    size_t n=(size_t)1<<l;
    printf("{\"type\":\"kernel\",\"id\":%llu,\"origin\":\"%s\",\"op\":\"%s\",\"logn\":%u,\"a\":",sequence++,origin,op,l);
    dump_mod(a,n);if(b){printf(",\"b\":");dump_mod(b,n);}printf(",\"out\":");dump_mod(y,n);puts("}");
}
static void save_file(const char *name,const void *data,size_t n)
{
    char path[2048];if(snprintf(path,sizeof path,"%s/%s",artifact_dir,name)>=(int)sizeof path)fail("path");
    FILE *f=fopen(path,"wb");if(!f||fwrite(data,1,n,f)!=n||fclose(f))fail("save");
}
static void workload(unsigned logn)
{
    if(logn!=9&&logn!=10)fail("logn");
    unsigned char seed[48];for(unsigned i=0;i<sizeof seed;i++)seed[i]=(unsigned char)(i+17*logn);
    shake256_context rng;shake256_init_prng_from_seed(&rng,seed,sizeof seed);
    size_t sklen=FALCON_PRIVKEY_SIZE(logn),pklen=FALCON_PUBKEY_SIZE(logn),eklen=FALCON_EXPANDEDKEY_SIZE(logn);
    size_t cap=FALCON_SIG_COMPRESSED_MAXSIZE(logn),tmplen=FALCON_TMPSIZE_KEYGEN(logn);
    if(tmplen<FALCON_TMPSIZE_EXPANDPRIV(logn))tmplen=FALCON_TMPSIZE_EXPANDPRIV(logn);
    if(tmplen<FALCON_TMPSIZE_SIGNTREE(logn))tmplen=FALCON_TMPSIZE_SIGNTREE(logn);
    if(tmplen<FALCON_TMPSIZE_VERIFY(logn))tmplen=FALCON_TMPSIZE_VERIFY(logn);
    void *sk=alloc_bytes(sklen),*pk=alloc_bytes(pklen),*ek=alloc_bytes(eklen),*tmp=alloc_bytes(tmplen);
    unsigned char *sig=alloc_bytes(cap);
    origin="keygen";int kg=falcon_keygen_make(&rng,logn,sk,sklen,pk,pklen,tmp,tmplen);
    if(kg)fail("keygen");save_file("sk.bin",sk,sklen);save_file("pk.bin",pk,pklen);
    origin="expand_privkey";int ex=falcon_expand_privkey(ek,eklen,sk,sklen,tmp,tmplen);
    if(ex)fail("expand");save_file("expanded.bin",ek,eklen);
    for(unsigned trial=0;trial<2;trial++){
        char message[128],bad[128],name[40];size_t siglen=cap;
        int ml=snprintf(message,sizeof message,"FlexTransform live RTL substitution N=%u trial=%u",1u<<logn,trial);
        origin="sign_tree";
        int si=falcon_sign_tree(&rng,sig,&siglen,FALCON_SIG_COMPRESSED,ek,message,(size_t)ml,tmp,tmplen);
        if(si)fail("sign");origin="verify_valid";
        int ve=falcon_verify(sig,siglen,FALCON_SIG_COMPRESSED,pk,pklen,message,(size_t)ml,tmp,tmplen);
        if(ve)fail("valid signature rejected");
        memcpy(bad,message,(size_t)ml);bad[0]^=1;origin="verify_wrong_message";
        int wrong=falcon_verify(sig,siglen,FALCON_SIG_COMPRESSED,pk,pklen,bad,(size_t)ml,tmp,tmplen);
        if(!wrong)fail("wrong message accepted");
        origin="verify_wrong_signature";sig[siglen-1]^=1;
        int corrupt=falcon_verify(sig,siglen,FALCON_SIG_COMPRESSED,pk,pklen,message,(size_t)ml,tmp,tmplen);
        sig[siglen-1]^=1;if(!corrupt)fail("wrong signature accepted");
        snprintf(name,sizeof name,"sig%u.bin",trial);save_file(name,sig,siglen);
        snprintf(name,sizeof name,"msg%u.bin",trial);save_file(name,message,(size_t)ml);
        printf("{\"type\":\"application\",\"logn\":%u,\"trial\":%u,\"keygen\":%d,\"expand\":%d,\"sign\":%d,\"verify\":%d,\"wrong_message\":%d,\"wrong_signature\":%d,\"signature_bytes\":%zu}\n",logn,trial,kg,ex,si,ve,wrong,corrupt,siglen);
    }
    if(replacement){char extra[2];if(fscanf(replacement,"%1s",extra)==1)fail("unused replacement records");}
    printf("{\"type\":\"complete\",\"kernels\":%llu,\"replayed\":%s}\n",sequence,replacement?"true":"false");
    free(sk);free(pk);free(ek);free(tmp);free(sig);
}
int main(int argc,char **argv)
{
    if(argc!=5)return 3;
    if(!strcmp(argv[1],"replay")){replacement=fopen(argv[4],"r");if(!replacement)return 3;}
    else if(strcmp(argv[1],"capture"))return 3;
    artifact_dir=argv[3];
    if(!replacement){printf("{\"type\":\"rom\",\"words\":");dump_fpr(fpr_gm_tab,2048);puts("}");pqc_export_ntt();}
    workload((unsigned)atoi(argv[2]));if(replacement)fclose(replacement);return ferror(stdout)?5:0;
}
