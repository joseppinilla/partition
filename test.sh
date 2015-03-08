#!/bin/bash


echo BACKUP >> ./backup.txt
while read line
do
	echo $line >> ./backup.txt
done < ./results.txt

rm ./results.txt

FILES=./benchmarks/*

for s in 1 2 20 85 128
do
	for t in 1 5 10
	do
			for f in $FILES
			do
				echo "Placing $f benchmark..."
				time python ./placerA2/placerA2.py -q -t $t -s $s -i $f
			done

			total=0

			while read line
			do
					var=$((var+1))
					total=$((total+$line))
			done < ./results.txt

			echo $total/$var
			echo $((total / var)) >> ./average.txt
	done #Temp
done #Seed
