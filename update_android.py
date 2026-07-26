import os
os.chdir('/data/data/com.termux/files/home/alfredo-core')
with open('.env.satellite', 'r') as f:
    c = f.read()
c = c.replace('GAIN=2.0', 'GAIN=1.0')
with open('.env.satellite', 'w') as f:
    f.write(c)
os.system('git pull')
