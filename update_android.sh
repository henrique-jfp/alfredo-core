cat ~/alfredo-core/.env.satellite | sed 's/GAIN=2.0/GAIN=1.0/g' > ~/alfredo-core/.env.satellite.tmp
mv ~/alfredo-core/.env.satellite.tmp ~/alfredo-core/.env.satellite
cd ~/alfredo-core
git pull
