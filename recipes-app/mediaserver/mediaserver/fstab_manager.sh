#!/bin/bash

# examples:
#
# fstab_manager.sh false sda6  -  umount sda6
# fstab_manager.sh true sda7 "/mnt/TOSHIBA EXT2" ntfs-3g  -  mount sda7
#
#

FSTAB="fstab"

convert_spaces(){
    local path=$1
    local s=
    local c=
    for i in $(seq 1 ${#path})
    do
        c=${path:i-1:1}
				if [[ $c = ' ' ]]; then
            s="$s"$(printf '\\0%o' "'$c")
        else
				    s="$s"$c
				fi
    done
    echo  "$s"
}

remove_unused_disk(){
		local disks_in_fstab=$(cat $FSTAB | grep 'sd' | awk '{print $1}')
		local disks=$(ls -1 /dev/sd*)
    for val in $disks_in_fstab; do
		    valt=${val//'/dev/'}
				if ! [[ -e "$val" ]]; then
						sed -i '/'"${valt}"'/d' $FSTAB
				fi
    done
}

add_disk(){
		local device=$1
		local path=$2		
    local	device_type=$3
		local disks_in_fstab=$(cat $FSTAB | grep 'sd' | awk '{print $1}')

    if [[ $disks_in_fstab != *$device*  ]]; then
            echo "/dev/$device  $fstab_path  $device_type  rw,nofail  0  0" >> $FSTAB
		fi
}

remove_disk(){
		local device=$1
		sed -i '/'"${device}"'/d' $FSTAB
}

remove_unused_disk

mountDisk=$1
device=$2
path=$3
device_type=$4
fstab_path=$(convert_spaces "$path")

if [ $mountDisk == true ]; then
    add_disk $device $fstab_path $device_type
elif [ $mountDisk == false ];then
    remove_disk $device
fi



