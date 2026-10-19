#!/bin/bash
printf '******\nThe BUSCO Docker container is based on the biocontainer image (https://biocontainers.pro/). Here are a few tips.\nDo not use the root account. The default is biodocker (uid=1000), but you can specify your user id.\nYou need 
to use mounts (-v) to exchange files between the host filesystem, on which your user can write, and the container filesystem.\n`/busco_wd` is the default location in the container where inputs, outputs, and 
downloaded datasets are read and written. It is the default working directory when running the container.\n\nRun BUSCO as follows:\n`docker run -u $(id -u) -v 
$(pwd):/busco_wd ezlabgva/busco:v5.1.3_cv1 busco -h`\n\n'
busco -h
/bin/bash
