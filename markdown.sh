#!/bin/bash
cd PSP
for file in *.savepatch
do
	../parser ${file} -d > /dev/null
	echo ${file}
done
mv *.md ../docs/PSP/

cd ../PSV
for file in *.savepatch
do
	../parser ${file} -d > /dev/null
	echo ${file}
done
mv *.md ../docs/PSV/

cd ../PS3
for file in *.savepatch
do
	../parser ${file} -d > /dev/null
	echo ${file}
done
mv *.md ../docs/PS3/

cd ../PS4
for file in *.savepatch
do
	../parser ${file} -d > /dev/null
	echo ${file}
done
mv *.md ../docs/PS4/
