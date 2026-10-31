/* Independent original-C verifier: no replay hooks, no RTL substitutions. */
#include <stdio.h>
#include <stdlib.h>
#include "falcon.h"
static unsigned char *load(const char *path,size_t *n)
{
    FILE *f=fopen(path,"rb");if(!f)exit(3);fseek(f,0,SEEK_END);long z=ftell(f);rewind(f);
    if(z<0)exit(3);*n=(size_t)z;unsigned char *p=malloc(*n+1);
    if(!p||fread(p,1,*n,f)!=*n)exit(3);fclose(f);return p;
}
int main(int argc,char **argv)
{
    if(argc!=4)return 3;size_t pn,sn,mn;
    unsigned char *pk=load(argv[1],&pn),*sig=load(argv[2],&sn),*msg=load(argv[3],&mn);
    unsigned logn=pk[0]&15;if(logn!=9&&logn!=10)return 3;
    void *tmp=malloc(FALCON_TMPSIZE_VERIFY(logn));if(!tmp)return 3;
    int good=falcon_verify(sig,sn,FALCON_SIG_COMPRESSED,pk,pn,msg,mn,tmp,FALCON_TMPSIZE_VERIFY(logn));
    msg[0]^=1;
    int bad=falcon_verify(sig,sn,FALCON_SIG_COMPRESSED,pk,pn,msg,mn,tmp,FALCON_TMPSIZE_VERIFY(logn));
    printf("{\"valid\":%d,\"wrong_message\":%d}\n",good,bad);
    free(pk);free(sig);free(msg);free(tmp);return good||!bad?4:0;
}
