for i in $(seq 0 999); do hex=$(printf "0x%03X" "$i"); sed -i "s/\"up\": 0x[0-9A-Fa-f]\{3\}/\"up\": $hex/" canbus_client.py && python3 canbus_client.py up; done
