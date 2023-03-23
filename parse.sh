for a in data/*; do NAME=`basename "$a"`; php parse-logger.php "$a" > "out/$NAME.csv"; done;
