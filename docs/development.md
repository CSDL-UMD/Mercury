# Setting up the development environment on the dev instance

We have a development container set up on nobbs and called `mercury-dev`. This
document explains how to get access to it. Once one has access to it, it is
possible to set up PyCharm to work directly on the container from one's laptop.
It is not advisable to use a different IDE (like VScode) because it may mess
up the PyCharm environment.

## Prerequisites

You will need to provide Do Won with your public key. This is typically located
in a file called `id_rsa.pub`. Do NOT share the corresponding `id_rsa` file, as
that contains the private key, which should never be disclosed. There should
not be a password on this SSH key.

There is already a user called `mercury` on nobbs. Do Won has access to it, and
she can add your public key to it.

## 1. (For Do Won) Copy SSH key into container.

Assuming the public key of the new developer is `id_rsa_new.pub` then Do Won
will need to run these command from her laptop.
```
ssh-copy-id -i id_rsa_new.pub -o PubkeyAuthentication=no mercury@nobbs.umd.edu
ssh-copy-id -i id_rsa_new.pub -o PubkeyAuthentication=no ubuntu@mercury-dev
```

This is adding the key of the new team member on both the mercury user on nobbs (the host) and on the ubuntu user in the container.

## 2. (For the new team member) Set up a SSH gateway locally.

We need to set up passwordless login on the container (i.e. SSH key-based
authentication). The following assumes Do Won has already set up passwordless
login for you to connect to the host (in this case nobbs.umd.edu) as the
`mercury` user. 

To double check this is the case, you should be able to run
```
ssh mercury@nobbs.umd.edu
```
from your laptop and be able to access nobbs.

If that is the case, disconnect from nobbs, and in the terminal edit your SSH configuration file:
```
vim ~/.ssh/config
```

and add the following two blocks: first we tell SSH that nobbs will act as a gateway:

```
Host nobbs
    HostName nobbs.umd.edu
    User mercury

Host nobbsgw
    HostName nobbs.umd.edu
    User mercury
```

Then we tell SSH to use the gateway when trying to connect to the
container:

```
Host mercury-dev
    User ubuntu
    ProxyCommand ssh nobbsgw -W %h:%p
```

You should be able now to ssh into the container from your laptop without password:

```
ssh mercury-dev
```

If that worked, you can disconnect from the container:

```
exit
```

## 3. Set up PyCharm on your laptop

