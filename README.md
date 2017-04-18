# s3duplicity

#### REQUIREMENTS

s3duplicity needs duplicity. Install it or s3duplicity will be of no use for you.
Most distributions have readymade packages available.

Permsssion to your s3 bucket and AWS SNS services on an EC2 linux instance using arn/profile. 

#### Installation and configuration of s3duplicity

The following steps show you how to download, uncompress, and configure the **s3duplicity** on an EC2 Linux instance.

1. cd /opt/
2. sudo curl -L -o s3duplicity.zip https://github.com/sharondevop/s3duplicity/archive/master.zip
3. sudo unzip s3duplicity.zip
4. sudo mv s3duplicity-master s3duplicity
4. sudo rm s3duplicity.zip
5. cd s3duplicity
