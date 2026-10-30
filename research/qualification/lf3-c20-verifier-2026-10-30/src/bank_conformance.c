#define _POSIX_C_SOURCE 200809L
#include "bank_openssl.h"
#include "photonhash_lf3_c20_cached.h"
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void stop(const char *what,unsigned index) {
    fprintf(stderr,"{\"type\":\"STOP\",\"reason\":\"%s\",\"case\":%u}\n",what,index);
    FILE *f=fopen("evidence/STOP.json","wx");
    if(f) { fprintf(f,"{\"reason\":\"%s\",\"case\":%u}\n",what,index); fclose(f); }
    exit(40);
}
static int hex(uint8_t *out,size_t cap,const char *text) {
    size_t n=strcspn(text,"\r\n"); if(n%2 || n/2>cap) return -1;
    for(size_t i=0;i<n/2;i++) {
        unsigned v; char tmp[3]={text[2*i],text[2*i+1],0};
        if(sscanf(tmp,"%2x",&v)!=1) return -1;
        out[i]=(uint8_t)v;
    }
    return (int)(n/2);
}
int main(int argc,char **argv) {
    if(argc!=2) return 2;
    FILE *f=fopen(argv[1],"r"); if(!f) return 2;
    char *line=NULL;size_t cap=0;unsigned index=0,count=0,parents=0;
    uint8_t parent[32],last[32],header[4096],eh[32],ef[2048],ed[32];
    size_t length=0;uint64_t nonce=0;int have=0;
    ph_lf2_context_t bank={0};
    while(getline(&line,&cap,f)>0) {
        char field[32];int offset=0;
        if(sscanf(line,"case[%u].%31[^=]=%n",&index,field,&offset)!=2 || !offset) continue;
        const char *value=line+offset;
        if(!strcmp(field,"parent")) {
            if(hex(parent,32,value)!=32) return 3;
            if(!have || memcmp(parent,last,32)) {
                ph_lf2_context_free(&bank);
                ph_lf2_context_t portable={0};
                if(ph_lf2_context_init(&portable,parent)) return 3;
                for(unsigned workers=1;workers<=2;workers++) {
                    if(lf3_bank_openssl(&bank,parent,workers)) return 3;
                    for(unsigned p=0;p<8;p++) {
                        if(bank.matrices[p].n!=portable.matrices[p].n ||
                           memcmp(bank.matrices[p].seed,portable.matrices[p].seed,64) ||
                           memcmp(bank.matrices[p].checksum,portable.matrices[p].checksum,32) ||
                           memcmp(bank.matrices[p].m,portable.matrices[p].m,(size_t)4096*4096)) stop("OpenSSL full bank mismatch",index);
                    }
                    printf("{\"type\":\"full_bank_match\",\"parent_index\":%u,\"workers\":%u,\"coefficient_bytes_measured\":134217728,\"seeds_and_checksums_match\":true}\n",parents,workers);fflush(stdout);
                    if(workers==1) ph_lf2_context_free(&bank);
                }
                ph_lf2_context_free(&portable);memcpy(last,parent,32);have=1;parents++;
            }
        } else if(!strcmp(field,"header")) {
            int n=hex(header,sizeof header,value);if(n<0) return 3;length=(size_t)n;
        } else if(!strcmp(field,"nonce")) nonce=strtoull(value,NULL,10);
        else if(!strcmp(field,"h")) { if(hex(eh,32,value)!=32) return 3; }
        else if(!strcmp(field,"fold")) { if(hex(ef,2048,value)!=2048) return 3; }
        else if(!strcmp(field,"digest")) {
            uint8_t h[32],fold[2048],digest[32];
            if(hex(ed,32,value)!=32) return 3;
            if(ph_lf3_c20_hash_cached(digest,h,fold,&bank,header,length,nonce)) return 3;
            if(memcmp(eh,h,32)||memcmp(ef,fold,2048)||memcmp(ed,digest,32)) stop("C20 canonical vector mismatch",index);
            if(index!=count) return 3;
            count++;
        }
    }
    free(line);fclose(f);ph_lf2_context_free(&bank);
    if(count!=560||parents!=4) return 3;
    printf("{\"type\":\"complete\",\"vectors_matched_measured\":%u,\"parents_measured\":%u,\"full_bank_comparisons_measured\":8,\"mismatches_measured\":0}\n",count,parents);
    return 0;
}
