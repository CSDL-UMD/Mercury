# Deployment

These are the steps to perform deployment. The first part (steps 1--11) is
run on the host, in this case nobbs.umd.edu. Then, you need to run steps 12
and 13 locally on your development environment (which could be either your
laptop or a development instance).

## 1. Create a LXC instance

```
lxc launch images:ubuntu/20.04 mercury
```

## 2. Run a terminal in it

```
sudo lxc exec mercury -- /bin/bash
```

## 3. Install various packages: python-venv, ssh, and rsync (client and server)

```
apt update
apt install ssh rsync python3.10-venv libpq-dev
```

This installs the ssh client and server packages and starts the ssh server.

## 4. Enable public key authentication

Open the ssh configuration file:
```
vim /etc/ssh/sshd_config
```

Uncomment the following lines

```
PubkeyAuthentication yes
PasswordAuthentication yes
PermitEmptyPasswords no
```

## 5. Restart ssh server and start rsync

```
systemctl restart ssh
systemtcl start rsync
```

## 6. Set a password for the `ubuntu` user

```
passwd ubuntu
```

## 7. Exit the container

```
exit
```

## 8. Test that ubuntu user can login into container

```
sudo lxc console mercury
```

Enter `ubuntu` and the password set at step #6. If all went well you should
see the prompt `ubuntu@mercury:~$`. You can then exit again with `<ctrl>+a q`
and get back to the `ubuntu@nobbs:~$` prompt.

## 9. Set up IP of container in hosts file

First of all, you need to find the IP of the container:

```
sudo lxc list
```

Look for the `mercury` entry and copy the value in the `IPV4` column. Then edit `/etc/hosts`:

```
sudo vim /etc/hosts
```

and add an entry like this (where the IP corresponds to the value in the previous command.

```
10.224.109.29 mercury
```

## 10. Copy SSH key into container.

```
ssh-copy-id -i ~/.ssh/id_rsa -o PubkeyAuthentication=no mercury
```

## 11. Exit the host

```
exit
```

## 12. Set up a SSH gateway locally.

```
vim ~/.ssh/config
```

and add the following two blocks: first we tell SSH that nobbs will act as a gateway:

```
Host nobbs
    HostName nobbs.umd.edu

Host nobbsgw
    HostName nobbs.umd.edu
    User ubuntu
```

then we tell SSH to use the gateway when trying to connect to the container:

```
Host mercury
    User ubuntu
    ProxyCommand ssh nobbsgw -W %h:%p
```

You should be able now to ssh into the container from your laptop without password:

```
ssh mercury
```

If that worked, you can disconnect from the container:

```
exit
```

## 13. Run the deployment script locally

Now that you can connect to the container via SSH, you can run the deployment script:
```
./deploy.sh <CONF>
```

Here `<CONF>` is the production configuration file. The `deploy.sh` script
builds a wheel file, uploads it on the container, installs it in a virtual
environment, and finally installs a systemd service to run gunicorn with it.
