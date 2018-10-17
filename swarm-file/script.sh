#!/bin/bash

files="*.yaml"
regex="(worker-)([a-z-]+).yaml"
for f in $files
do
    if [[ $f =~ $regex ]]
    then
        mod="${BASH_REMATCH[2]}"
        echo "$model" 
        az vm show --name worker-$mod --resource-group cloud-asr-swarm -o table
        if [ $? -eq 0 ]        
        then
          echo "VM exist" 
        else
          echo "VM non found"
          az vm create --resource-group cloud-asr-swarm --name worker-$mod --location westeurope --size Standard_B2ms \
          --admin-username dev --ssh-key-value @~/Documenti/azure.pub --storage-sku Standard_LRS --vnet-name cloud-asr-swarm-vnet \
          --subnet default --public-ip-address """" --image Canonical:UbuntuServer:18.04-LTS:latest --custom-data cloud-init.txt

        fi 
    fi
done
