#!/bin/bash
# Linux 应急响应一键脚本（分隔符输出版）
# 运行方式：sudo bash emergency_response.sh

NOW=$(date +"%Y%m%d_%H%M%S")
REPORT="report/emergency_report_${NOW}.txt"
TMPDIR=$(mktemp -d /tmp/emergency.XXXXXX)

# 定义分隔符
SECTION_SEP="=========================================="
SUBSECTION_SEP="------------------------------------------"
MODULE_SEP="##########################################"


if [ "$EUID" -ne 0 ]; then
  echo "请以 root 或 sudo 权限运行本脚本！"
  exit 1
fi

if [ -f /etc/os-release ]; then
  . /etc/os-release
  OS=$ID
else
  OS=$(uname -s)
fi

if [ ! -d "report" ]; then
    mkdir -p report
fi

declare -A TAB_TITLES=(
  [backdoor]="系统后门排查"
  [user]="用户与登录检查"
  [log]="日志分析"
  [network]="网络检查"
  [process]="进程检查"
  [filesystem]="文件系统检查"
  [package]="软件包检查"
  [persistence]="持久化检查"
  [integrity]="系统完整性"
  [malware]="恶意进程与提权点"
  [summary]="功能总结与使用说明"
)

# 函数：打印当前执行模块
print_module() {
  echo "正在执行模块：$1"
}

# 函数：写入章节标题
write_section() {
  echo "$MODULE_SEP"
  echo "模块: $1"
  echo "$SECTION_SEP"
}

# 函数：写入子章节
write_subsection() {
  echo "$SUBSECTION_SEP"
  echo "子项: $1"
  echo "$SUBSECTION_SEP"
}

# 4. 网络检查
network_check() {
  print_module "${TAB_TITLES[network]}"
  {
    write_section "${TAB_TITLES[network]}"
    
    write_subsection "监听端口"
    ss -tulnp 2>/dev/null || netstat -tulnp 2>/dev/null
    
    write_subsection "活动连接"
    ss -antp 2>/dev/null || netstat -antp 2>/dev/null
    
    write_subsection "网络配置"
    ip addr 2>/dev/null || ifconfig -a 2>/dev/null
    
    write_subsection "路由表"
    ip route 2>/dev/null || route -n 2>/dev/null
    
    write_subsection "可疑连接"
    ss -antp 2>/dev/null | grep ESTAB | grep -E ':[0-9]+.*[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+' | grep -v '127\.0\.0\.1' || true
  } >> "$REPORT"
}

# 1. 系统后门排查
backdoor_check() {
  print_module "${TAB_TITLES[backdoor]}"
  {
    write_section "${TAB_TITLES[backdoor]}"
    
    write_subsection "UID为0的非root用户"
    awk -F: '($3 == 0 && $1 != "root"){print "可疑UID 0用户: "$1}' /etc/passwd
    
    write_subsection "可疑系统配置"
    echo "检查系统配置文件权限:"
    ls -l /etc/passwd /etc/shadow /etc/group /etc/sudoers 2>/dev/null
    echo "检查异常的系统配置:"
    find /etc -type f -mtime -7 -ls 2>/dev/null | grep -E 'conf$|cnf$|cfg$'
    
    write_subsection "异常系统文件"
    echo "检查关键目录下的异常文件:"
    find /bin /sbin /usr/bin /usr/sbin -type f -mtime -7 -ls 2>/dev/null
    echo "检查异常的系统库文件:"
    find /lib /lib64 /usr/lib -type f -mtime -7 -ls 2>/dev/null | head -n 20
  } >> "$REPORT"
}

# 2. 用户与登录检查
user_check() {
  print_module "${TAB_TITLES[user]}"
  {
    write_section "${TAB_TITLES[user]}"
    
    write_subsection "当前用户"
    whoami
    
    write_subsection "所有用户"
    awk -F: '{print $1}' /etc/passwd
    
    write_subsection "最近登录记录"
    last -a -n 20 2>/dev/null
    
    write_subsection "登录失败记录"
    lastb -a -n 20 2>/dev/null || echo "lastb 未安装"
  } >> "$REPORT"
}

# 3. 日志分析
log_check() {
  print_module "${TAB_TITLES[log]}"
  {
    write_section "${TAB_TITLES[log]}"
    
    write_subsection "系统日志错误"
    grep -Ei 'error|fail|denied|refused|invalid|segfault|unauthorized|attack|panic' /var/log/syslog /var/log/messages 2>/dev/null | tail -n 50
    
    write_subsection "安全日志错误"
    grep -Ei 'fail|invalid|root|attack|sudo|su:|authentication failure' /var/log/auth.log /var/log/secure 2>/dev/null | tail -n 50
  } >> "$REPORT"
}

# 5. 进程检查
process_check() {
  print_module "${TAB_TITLES[process]}"
  {
    write_section "${TAB_TITLES[process]}"
    
    write_subsection "高CPU占用进程"
    ps aux --sort=-%cpu | head -n 15
    
    write_subsection "可疑脚本进程"
    ps aux | grep -E 'bash|sh|python|perl|php|nc|netcat|socat' | grep -vE 'grep|emergency_response.sh' | awk '{print $2, $11}'
  } >> "$REPORT"
}

# 6. 文件系统检查
filesystem_check() {
  print_module "${TAB_TITLES[filesystem]}"
  {
    write_section "${TAB_TITLES[filesystem]}"
    
    write_subsection "SUID文件"
    find / \( -path /proc -o -path /sys -o -path /dev -o -path /run -o -path /tmp -o -path /var/lib/docker \) -prune -o -perm -4000 -type f -exec ls -l {} \; 2>/dev/null
    
    write_subsection "最近修改的文件"
    find / \( -path /proc -o -path /sys -o -path /dev -o -path /run -o -path /tmp -o -path /var/lib/docker \) -prune -o -type f -mtime -7 -exec ls -l {} \; 2>/dev/null | head -n 50
  } >> "$REPORT"
}

# 7. 软件包检查
package_check() {
  print_module "${TAB_TITLES[package]}"
  {
    write_section "${TAB_TITLES[package]}"
    
    write_subsection "已安装的软件包"
    if [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
      dpkg -l | grep '^ii' | awk '{print $2, $3}' 2>/dev/null
    elif [[ "$OS" == "centos" || "$OS" == "rhel" ]]; then
      rpm -qa --queryformat '%{NAME} %{VERSION}-%{RELEASE}\n' 2>/dev/null
    else
      echo "未知系统，无法列出软件包"
    fi
  } >> "$REPORT"
}

# 8. 持久化检查
persistence_check() {
  print_module "${TAB_TITLES[persistence]}"
  {
    write_section "${TAB_TITLES[persistence]}"
    
    write_subsection "自启动服务"
    systemctl list-unit-files --type=service --state=enabled 2>/dev/null
    
    write_subsection "计划任务"
    echo "系统计划任务:"
    cat /etc/crontab 2>/dev/null
    echo "Cron目录内容:"
    ls -l /etc/cron* /var/spool/cron/* 2>/dev/null
    echo "用户计划任务:"
    for u in $(cut -f1 -d: /etc/passwd); do
      crontab -l -u "$u" 2>/dev/null | grep -v '^#' && echo "用户: $u" || true
    done
    
    write_subsection "SSH公钥"
    for u in $(cut -f1 -d: /etc/passwd); do
      home=$(eval echo ~"$u")
      if [ -f "$home/.ssh/authorized_keys" ]; then
        echo "用户 $u 的SSH密钥:"
        cat "$home/.ssh/authorized_keys" 2>/dev/null
      fi
    done
    
    write_subsection "启动项配置"
    echo "RC启动脚本:"
    ls -l /etc/rc*.d/ 2>/dev/null
    echo "RC Local内容:"
    cat /etc/rc.local 2>/dev/null
    echo "Systemd用户服务:"
    ls -l /etc/systemd/system/*.service /usr/lib/systemd/system/*.service 2>/dev/null
    echo "Init.d脚本:"
    ls -l /etc/init.d/ 2>/dev/null
  } >> "$REPORT"
}

# 9. 系统完整性检查
integrity_check() {
  print_module "${TAB_TITLES[integrity]}"
  {
    write_section "${TAB_TITLES[integrity]}"
    
    write_subsection "关键二进制文件校验"
    for bin in /bin/ls /bin/ps /bin/netstat /usr/bin/ss /bin/bash /usr/bin/sudo; do
      [ -f "$bin" ] && sha256sum "$bin" 2>/dev/null
    done
    
    write_subsection "系统文件完整性"
    if [[ "$OS" == "centos" || "$OS" == "rhel" ]]; then
      rpm -Va --nomtime --nosize --nomd5 | grep -v '^..5......' 2>/dev/null
    elif [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
      debsums -s 2>/dev/null || echo "未安装 debsums"
    fi
  } >> "$REPORT"
}

# 10. 恶意进程与提权点检查
malware_check() {
  print_module "${TAB_TITLES[malware]}"
  {
    write_section "${TAB_TITLES[malware]}"
    
    write_subsection "可疑进程"
    ps aux | grep -E 'kworker|kthreadd|crypto|minerd|\.tmp|\.sh|\.py|\.pl|\.php|/tmp|/dev/shm' | grep -vE 'grep|emergency_response.sh' | awk '{print $2, $11}'
    
    write_subsection "可疑提权点"
    find / \( -path /proc -o -path /sys -o -path /dev -o -path /run -o -path /tmp -o -path /var/lib/docker \) -prune -o -perm -4000 -type f -exec ls -l {} \; 2>/dev/null | grep -E 'nmap|perl|python|find|awk|vim|nano|less|more|cp|mv|bash|sh'
    
    write_subsection "隐藏文件"
    find / \( -path /proc -o -path /sys -o -path /dev -o -path /run -o -path /tmp -o -path /var/lib/docker \) -prune -o \( -name ".*" -type f -o -name ".*" -type d \) -exec ls -l {} \; 2>/dev/null
  } >> "$REPORT"
}



# 执行所有检查
{
  echo "Linux 应急响应报告"
  echo "生成时间: $(date)"
  echo "$MODULE_SEP"
  echo
} > "$REPORT"

backdoor_check
user_check
log_check
network_check
process_check
filesystem_check
package_check
persistence_check
integrity_check
malware_check

rm -rf "$TMPDIR"
echo "应急响应报告已生成：$REPORT"
echo "请使用文本编辑器查看该报告。"

