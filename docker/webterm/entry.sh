#!/bin/bash
WETTY_PASSWORD=$1
echo $WETTY_PASSWORD
sed -i 's#%WETTY_PASSWORD%#'$WETTY_PASSWORD'#g' /app/public/wetty/index.html /app/public/index.html /app/public/wetty/wetty.js
node /app/app.js --urlPath /$WETTY_PASSWORD --sslkey /ssl/ipt-compute_tacc_cloud_key.pem --sslcert /ssl/ipt-compute_tacc_cloud_bundle.cer -p 3000
