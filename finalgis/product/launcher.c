#define _DARWIN_C_SOURCE
#include <mach-o/dyld.h>
#include <sys/stat.h>
#include <unistd.h>
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifndef FINALGIS_PROFILE
#error FINALGIS_PROFILE must name the isolated profile root
#endif
int main(int argc, char **argv) {
    char executable[PATH_MAX], real[PATH_MAX], resource[PATH_MAX], engine[PATH_MAX], config[PATH_MAX];
    uint32_t size = sizeof(executable);
    if (_NSGetExecutablePath(executable, &size) || !realpath(executable, real)) return 2;
    char *slash = strrchr(real, '/'); if (!slash) return 2; *slash = 0;
    if (snprintf(engine, sizeof(engine), "%s/FinalGIS-engine", real) >= (int)sizeof(engine) ||
        snprintf(resource, sizeof(resource), "%s/../Resources/FinalGIS", real) >= (int)sizeof(resource) ||
        snprintf(config, sizeof(config), "%s/finalgis-config.json", resource) >= (int)sizeof(config)) return 2;
    for (int i=1;i<argc;i++) {
        const char *blocked[]={"--profiles-path","--profile","--customizationfile","--configpath","--optionspath"};
        for (size_t j=0;j<sizeof(blocked)/sizeof(*blocked);j++)
            if (!strcmp(argv[i],blocked[j]) || (!strncmp(argv[i],blocked[j],strlen(blocked[j])) && argv[i][strlen(blocked[j])]=='=')) {
                fputs("FinalGIS uses its isolated product profile.\n",stderr);return 2;
            }
    }
    char customization[PATH_MAX];
#ifdef FINALGIS_QGIS4
    /* QGIS 4 reads GUI customization as XML (version 1); only the splash path is set. */
    if (snprintf(customization,sizeof(customization),"%s/finalgis-customization.xml",FINALGIS_PROFILE)>=(int)sizeof(customization))return 2;
    FILE *f=fopen(customization,"w"); if (!f)return 2;
    fprintf(f,"<!DOCTYPE customization>\n<Customization version=\"1\" enabled=\"true\" splashPath=\"%s/branding/\"/>\n",resource);if(fclose(f))return 2;
#else
    if (snprintf(customization,sizeof(customization),"%s/finalgis-customization.ini",FINALGIS_PROFILE)>=(int)sizeof(customization))return 2;
    FILE *f=fopen(customization,"w"); if (!f)return 2;
    fprintf(f,"[Customization]\nsplashpath=%s/branding/\n",resource);if(fclose(f))return 2;
#endif
    setenv("FINALGIS_CONFIG", config, 1);setenv("PROJ_NETWORK","OFF",1);
    char **args=calloc((size_t)argc+7,sizeof(char*));if(!args)return 2;
    args[0]=engine;for(int i=1;i<argc;i++)args[i]=argv[i];
    args[argc]="--profiles-path";args[argc+1]=FINALGIS_PROFILE;
    args[argc+2]="--profile";args[argc+3]="FinalGIS";
    args[argc+4]="--customizationfile";args[argc+5]=customization;
    execv(engine,args);perror("FinalGIS engine");free(args);return 2;
}
