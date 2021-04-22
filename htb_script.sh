#!/bin/bash


#  kbps: Kilobytes per second
#  mbps: Megabytes per second
#  kbit: Kilobits per second
#  mbit: Megabits per second
#  bps: Bytes per second
#       Amounts of data can be specified in:
#       kb or k: Kilobytes
#       mb or m: Megabytes
#       mbit: Megabits
#       kbit: Kilobits
#usunąć wszelkie qdiski można za pomocą "tc qdisc del dev br-lan root"
#exemplary usage "./htb_skrypt.sh -h 192.168.2.15/32 -d 10mbit"

TC=tc
IP=/usr/libexec/ip
IF=br-lan             
# Interface
U32="$TC filter add dev $IF protocol ip parent 1:0 prio 1 u32"

#this is the function to set a different name of the interface
set_interface()
{
IF=$1
echo $IF
}
remove_download()
{
#we remove the root qdisc for download at the interface, thus removing all subclasses
tc qdisc del dev $IF root 
}





htb_init ()
{
  $TC qdisc add dev $IF root handle 1: htb default 1
}




#pass ip, port and download rate as argument
set_download()
{
    local OPTIND=1
    local arg src_ip dst_ip s_port d_port d_rate d_delay d_loss
    src_ip=${src_ip:-0.0.0.0/0}
    dst_ip=${dst_ip:-0.0.0.0/0}
    while getopts 's:d:p:o:r:l:m:' arg
    do
        case ${arg} in
            s) src_ip=${OPTARG};;
            d) dst_ip=${OPTARG};;
            p) s_port=${OPTARG};;
            o) d_port=${OPTARG};;
            r) d_rate=${OPTARG};;
            l) d_delay=${OPTARG};;
            m) d_loss=${OPTARG};;
        
        esac
    done 
    shift $((OPTIND -1))
    read q_num < q_num.txt
    # check if root to which we can bind a class already exists:
    checkroot=$( tc qdisc show dev $IF | grep "htb 1:" )
    
    if [ -z "$checkroot" ]
    then
      $TC qdisc add dev $IF root handle 1: htb default 30
    fi
    q_num=$((q_num+1))
    echo "New classid for download: $q_num "
    echo "Download rate is: ${d_rate}"
    $TC class add dev $IF parent 1: classid 1:${q_num} htb rate ${d_rate} ceil ${d_rate}
    
    if [[ ! -z $d_delay ]] && [[ ! -z $d_loss ]]
    then
        $TC qdisc add dev $IF parent 1:$q_num handle $q_num: netem delay $d_loss delay $d_delay
    elif [[ ! -z $d_delay ]]
    then
        $TC qdisc add dev $IF parent 1:$q_num handle $q_num: netem loss $d_delay
    elif [[ ! -z $d_loss ]]
    then
        $TC qdisc add dev $IF parent 1:$q_num handle $q_num: netem loss $d_loss 
    
    fi
    
    
    if [[ ! -z $d_port ]] && [[ ! -z $s_port ]]
    then
	    echo "both port set" 
        $U32 match ip src $src_ip match ip dst $dst_ip match ip dport $d_port 0xffff match ip sport $s_port 0xffff flowid 1:$q_num 
    elif [[ ! -z $d_port ]]
    then 
        echo "d_port set"
        $U32 match ip src $src_ip match ip dst $dst_ip match ip dport $d_port 0xffff flowid 1:$q_num
    
    elif [[ ! -z $s_port ]]
    then 
        echo "s_port set"
        $U32 match ip src $src_ip match ip dst $dst_ip match ip sport $d_port 0xffff flowid 1:$q_num
    else      
        $U32 match ip src $src_ip match ip dst $dst_ip flowid 1:$q_num      
    fi  
    echo $q_num > q_num.txt
    
}


set_upload()
{
    local OPTIND=1
    local arg src_ip dst_ip s_port d_port u_rate u_delay u_loss
    src_ip=${src_ip:-0.0.0.0/0}
    dst_ip=${dst_ip:-0.0.0.0/0}
    while getopts 's:d:p:o:r:l:m:' arg
    do
        case ${arg} in
            s) src_ip=${OPTARG};;
            d) dst_ip=${OPTARG};;
            p) s_port=${OPTARG};;
            o) d_port=${OPTARG};;
            r) u_rate=${OPTARG};;
            l) u_delay=${OPTARG};; 
            m) u_loss=${OPTARG};;         
        esac
    done 
    shift $((OPTIND -1))
    read q_num < q_num.txt
    q_num=$((q_num+1))  
    echo "New classid for upload is: $q_num"
    echo "Upload rate is: ${u_rate}"
    ifb_id="ifb123"
    echo $ifb_id
    U322="$TC filter add dev $ifb_id protocol ip parent 1a1a: prio 1 u32"
    # it has to know the name of ifb, otherwise takes protocol for the name
    modprobe ifb
    $IP link add $ifb_id type ifb
    $IP link set dev $ifb_id up 
    #tworzenie obiektu ifb jako nowego dev do mirrorowania ruchu
    $TC qdisc add dev $IF ingress 
    $TC filter add dev $IF parent ffff: protocol ip u32 match u32 0 0 flowid 1a1a: action mirred egress redirect dev ${ifb_id}
    $TC qdisc add dev ${ifb_id} root handle 1a1a: htb default 1
    $TC class add dev ${ifb_id} parent 1a1a: classid 1a1a:1 htb rate 32000000.0kbit 
    
    $TC class add dev ${ifb_id} parent 1a1a: classid 1a1a:${q_num} htb rate ${u_rate} ceil ${u_rate} 
    
    if [[ ! -z $u_delay ]] && [[ ! -z $u_loss ]]
    then
        $TC qdisc add dev $ifb_id parent 1:$q_num handle $q_num: netem loss $u_loss delay $u_delay
    elif [[ ! -z $u_delay ]]
    then
        $TC qdisc add dev $ifb_id parent 1:$q_num handle $q_num: netem delay $u_delay
    elif [[ ! -z $u_loss ]]
    then
        $TC qdisc add dev $ifb_id parent 1:$q_num handle $q_num: netem loss $u_loss 
    
    fi
    

    
    if [[ ! -z $d_port ]] && [[ ! -z $s_port ]]
    then
	    echo "both port set" 
        $U322 match ip src $src_ip match ip dst $dst_ip match ip dport $d_port 0xffff match ip sport $s_port 0xffff flowid 1a1a:$q_num 
    elif [[ ! -z $d_port ]]
    then 
        echo "d_port set"
        $U322 match ip src $src_ip match ip dst $dst_ip match ip dport $d_port 0xffff flowid 1a1a:$q_num
    
    elif [[ ! -z $s_port ]]
    then 
        echo "s_port set"
        $U322 match ip src $src_ip match ip dst $dst_ip match ip sport $d_port 0xffff flowid 1a1a:$q_num
        

    else

        
        $U322 match ip src $src_ip match ip dst $dst_ip flowid 1a1a:$q_num
        
    fi  
    echo $q_num > q_num.txt

}

remove_upload()
{
    
    tc qdisc del dev $IF ingress
    tc qdisc del dev $ifb_id root
    
}







