#!/bin/bash -x

LOGDIR=/var/log/cray

SATMANDIR=/usr/share/man/man8
SLINGSHOT_TOOLS_REPO=https://stash.us.cray.com/scm/SSHOT/slingshot_tools.git
SLINGSHOT_TOOLS_DIR=slingshot_tools
SLINGSHOT_TOOLS_BRANCH=master

CRAYCTL_REPO=https://stash.us.cray.com/scm/MTL/crayctl.git
CRAYCTL_DIR=crayctl
CRAYCTL_BRANCH=master
BMC_ROOT_PASSWORD=${BMC_ROOT_PASSWORD:-"**password**"}

# create logging directory
if [ ! -d "$LOGDIR" ]; then
    mkdir -p $LOGDIR
    chmod 755 $LOGDIR
fi

# generate sat.toml
cd /sat
python3 tools/generate_default_config.py -o /etc/sat.toml sat/config.py

# make man pages
cd /sat/docs/man
make

# install man pages
cd /sat
if [ ! -d "$SATMANDIR" ]; then
    mkdir -p $SATMANDIR
    chmod 755 $SATMANDIR
fi
cp docs/man/*.8 $SATMANDIR

# generate auto-completion script
cd /sat
if [ ! -d "/etc/bash_completion.d" ]; then
    mkdir -p /etc/bash_completion.d
    chmod 755 /etc/bash_completion.d
fi
register-python-argcomplete sat > /etc/bash_completion.d/sat-completion.bash
echo "source /etc/bash_completion.d/sat-completion.bash" >> /root/.bash_login

# install slingshot-tools
cd /sat
git clone $SLINGSHOT_TOOLS_REPO $SLINGSHOT_TOOLS_DIR
cd  $SLINGSHOT_TOOLS_DIR
git checkout $SLINGSHOT_TOOLS_BRANCH
python3 setup.py install --root=/

# install ipmitools scripts
cd /sat
if [ ! -d "/root/bin" ]; then
    mkdir /root/bin
    chmod 755 /root/bin
fi
git clone $CRAYCTL_REPO $CRAYCTL_DIR
cd  $CRAYCTL_DIR
git checkout $CRAYCTL_BRANCH
ansible localhost -m ansible.builtin.copy \
    -a "src=/sat/crayctl/ansible_framework/main/templates/ipmi_console_stop.sh dest=/root/bin/ipmi_console_stop.sh mode=0755"
ansible localhost -m ansible.builtin.template \
    -a "src=/sat/crayctl/ansible_framework/main/templates/ipmi_console_start.sh.j2 dest=/root/bin/ipmi_console_start.sh mode=0755" \
    --extra-vars "bmc_root_password=$BMC_ROOT_PASSWORD"
