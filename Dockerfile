from quay.io/biocontainers/busco:5.6.1--pyhdfd78af_0

################## METADATA ######################
LABEL base.image="biocontainers/biocontainers:v1.1.0_cv2"
LABEL version="v5.6.1"
LABEL software="BUSCO:Benchmarking Universal Single-Copy Orthologs"
LABEL software.version="5.6.1"
LABEL about.summary="Biodocker for BUSCO:Benchmarking Universal Single-Copy Orthologs"
LABEL about.home="https://busco.ezlab.org/"
LABEL about.documentation="https://busco.ezlab.org/busco_userguide.html"
LABEL license="https://gitlab.com/ezlab/busco/blob/master/LICENSE"
LABEL about.tags="genomics, transcriptomics, metagenomics, bioinformatics, evolution"

################## MAINTAINER ######################
MAINTAINER BUSCO Team <support@orthodb.org>

# Switch back to root for some install

USER root
WORKDIR /busco_wd

RUN groupadd busco_users &&\
    useradd --create-home --shell /bin/bash --user-group --uid 1000 --groups busco_users busco_user &&\
    chown busco_user:busco_users /busco_wd && \
    chmod -R 777 /usr/local/config

# Go to the busco user
USER busco_user
