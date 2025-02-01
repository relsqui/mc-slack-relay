names=(Rocky Bullwinkle Boris Natasha)
ends=('' '' '' '' '' '.' '.' '.' '.' '?' '!' '..' '...' ',' '!!' '?!')

random_from() {
  index=$(( ($RANDOM % $#) + 1 ))
  echo "${!index}"
}

make_message() {
  length=$(( ($RANDOM % 10) + 1 ))
  words=$(cat /usr/share/dict/words | grep -v "[A-Z']" | shuf -n $length | tr '\n' ' ' | sed 's/\W*$//')
  echo -n "$words"
  random_from "${ends[@]}"
}

chat() {
  chatter=$(random_from "${names[@]}")
  message=$(make_message)
  echo "$chatter: $message"
}

echo "Joined the chat."
while true; do
  read -t $(( $RANDOM / 2000 )) heard && echo "User: ${heard}"
  chat
  if [ "$heard" = "stop" ]; then
    break
  fi
done
echo "Goodbye!"