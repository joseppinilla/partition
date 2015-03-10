#!/bin/bash


echo BACKUP >> ./backup.txt
while read line
do
	echo $line >> ./backup.txt
done < ./results.txt

rm ./results.txt

FILES=./benchmarks/*


for f in $FILES
do
	python ./partitionA3/partitionA3.py -q -i $f
done
