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


TC=tc
IP=/usr/libexec/ip
IF=br-lan             
# Interface
U32="$TC filter add dev $IF protocol ip parent 1:0 prio 1 u32"

#ustawienie innej nazwy interfejsu
set_interface()
{
IF=$1
echo $IF
}

remove_download()
{
#funkcja do usuwania qdiscu root dla interfejsu a tym samym usuniecia wszystkich zasad
tc qdisc del dev $IF root 
}

remove_upload()
{
#funkcja do usuwania ifb root tym samym usuwajaca wszystkie zasady wysylania
    tc qdisc del dev $IF ingress
    tc qdisc del dev $ifb_id root
    
}




htb_init ()
{
#funkcja inicjalizujaca
  $TC qdisc add dev $IF root handle 1: htb default 1
}





set_download()
{
    local OPTIND=1
    local arg src_ip dst_ip s_port d_port d_rate d_delay d_loss
    #deklaracja lokalnych zmiennych: zrodlowy adres IP, docelowy adres IP, zrodlowy port, docelowy port, predkosc pobierania, opoznienie ms, utrata pakietow %
    src_ip=${src_ip:-0.0.0.0/0}
    dst_ip=${dst_ip:-0.0.0.0/0}
    #domyslne wartosci adresow zrodlowych i docelowych uzyte w filtrze oznaczaja, ze przepuszczane sa wszystkie adresy zrodlowe i docelowe
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
    #q_num to zmienna słuzaca do nadawania klasom ID, przechowywana w osobnym pliku, zeby uniknac konfliktu nazw
    
    checkroot=$( tc qdisc show dev $IF | grep "htb 1:" )
    #warunek sprawdzajacy czy istnieje qdisc root, jesli nie, tworzy się go
    if [ -z "$checkroot" ]
    then
      $TC qdisc add dev $IF root handle 1: htb default 30
    fi
    q_num=$((q_num+1))
    echo "New classid for download: $q_num "
    echo "Download rate is: ${d_rate}"
    #dodanie qdiscu o okreslonych parametrach rate i ceil
    $TC class add dev $IF parent 1: classid 1:${q_num} htb rate ${d_rate} ceil ${d_rate}
    #warunki do uwzględniania opoznienia i utraty pakietow
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
    
    #warunki uwzgledniajace ustawione porty i dodające filtry
    if [[ ! -z $d_port ]] && [[ ! -z $s_port ]]
    then
        $U32 match ip src $src_ip match ip dst $dst_ip match ip dport $d_port 0xffff match ip sport $s_port 0xffff flowid 1:$q_num 
    elif [[ ! -z $d_port ]]
    then 

        $U32 match ip src $src_ip match ip dst $dst_ip match ip dport $d_port 0xffff flowid 1:$q_num
    
    elif [[ ! -z $s_port ]]
    then 

        $U32 match ip src $src_ip match ip dst $dst_ip match ip sport $d_port 0xffff flowid 1:$q_num
    else      
        $U32 match ip src $src_ip match ip dst $dst_ip flowid 1:$q_num      
        #jesli zaden port nie jest ustawiony w filtrze uwzgledniane sa tylko adresy IP
    fi  
    #zapisanie zmiennej q_num 
    echo $q_num > q_num.txt
    
}


set_upload()
{
    local OPTIND=1
    local arg src_ip dst_ip s_port d_port u_rate u_delay u_loss
    #deklaracja lokalnych zmiennych: zrodlowy adres IP, docelowy adres IP, zrodlowy port, docelowy port, predkosc wysylania, opoznienie ms, utrata pakietow %
    src_ip=${src_ip:-0.0.0.0/0}
    dst_ip=${dst_ip:-0.0.0.0/0}
    #domyslne wartosci adresow zrodlowych i docelowych uzyte w filtrze oznaczaja, ze przepuszczane sa wszystkie adresy zrodlowe i docelowe
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
    #q_num to zmienna słuzaca do nadawania klasom ID, przechowywana w osobnym pliku, zeby uniknac konfliktu nazw
    q_num=$((q_num+1))  
    echo "New classid for upload is: $q_num"
    echo "Upload rate is: ${u_rate}"
    ifb_id="ifb123"
    echo $ifb_id
    U322="$TC filter add dev $ifb_id protocol ip parent 1a1a: prio 1 u32"
    
    modprobe ifb
    $IP link add $ifb_id type ifb
    $IP link set dev $ifb_id up 
    #tworzenie obiektu ifb jako nowego dev do mirrorowania ruchu
    $TC qdisc add dev $IF ingress 
    $TC filter add dev $IF parent ffff: protocol ip u32 match u32 0 0 flowid 1a1a: action mirred egress redirect dev ${ifb_id}
    #stworzenie domyslnego qdiscu za pomoca wirtualnego interfejsu ifb
    $TC qdisc add dev ${ifb_id} root handle 1a1a: htb default 1
    $TC class add dev ${ifb_id} parent 1a1a: classid 1a1a:1 htb rate 32000000.0kbit 
    #dodanie qdiscu o okreslonych parametrach rate i ceil
    $TC class add dev ${ifb_id} parent 1a1a: classid 1a1a:${q_num} htb rate ${u_rate} ceil ${u_rate} 
    #warunki do uwzględniania opoznienia i utraty pakietow
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
    

    #warunki uwzgledniajace ustawione porty i dodające filtry
    if [[ ! -z $d_port ]] && [[ ! -z $s_port ]]
    then
        $U322 match ip src $src_ip match ip dst $dst_ip match ip dport $d_port 0xffff match ip sport $s_port 0xffff flowid 1a1a:$q_num 
    elif [[ ! -z $d_port ]]
    then 
        $U322 match ip src $src_ip match ip dst $dst_ip match ip dport $d_port 0xffff flowid 1a1a:$q_num
    
    elif [[ ! -z $s_port ]]
    then 
        $U322 match ip src $src_ip match ip dst $dst_ip match ip sport $d_port 0xffff flowid 1a1a:$q_num
        

    else

        
        $U322 match ip src $src_ip match ip dst $dst_ip flowid 1a1a:$q_num
            #jesli zaden port nie jest ustawiony w filtrze uwzgledniane sa tylko adresy IP
    fi  
    #zapisanie zmiennej q_num
    echo $q_num > q_num.txt

}









