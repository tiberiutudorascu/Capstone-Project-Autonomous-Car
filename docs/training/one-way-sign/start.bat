mkdir n ::Aici se adauga poze,frameuri care NU contin deloc semnul!

dir /b /s n\*.jpg > neg.txt

mkdir data REM Aici se adauga datele finale

opencv_createsamples.exe -img semn.png -bg neg.txt -info info.txt -num 2500 -maxxangle 0.5 -maxyangle 0.5 -maxzangle 0.5 -w 32 -h 32 -vec pos1.vec

opencv_createsamples.exe -img semn2.png -bg neg.txt -info info.txt -num 2500 -maxxangle 0.5 -maxyangle 0.5 -maxzangle 0.5 -w 32 -h 32 -vec pos2.vec

opencv_createsamples.exe -img semn3.png -bg neg.txt -info info.txt -num 2500 -maxxangle 0.5 -maxyangle 0.5 -maxzangle 0.5 -w 32 -h 32 -vec pos3.vec

::Se pot adauga oricate poze aici, doar ca trebuie modificata lista din scriptul python.

python3 vec-files-merge.py

opencv_traincascade.exe ^
-data data ^
-vec final_positives.vec ^
-bg neg.txt ^
-numPos 5000 ^  REM La fel in functie de cate date sunt scoase din fisierul vec final se poate modifica aici cu -1000 fata de cate mostre au iesit
-numNeg 2000 ^  REM Analog aici
-numStages 20 ^
-w 32 -h 32 ^
-featureType LBP ^
-minHitRate 0.999 ^
-maxFalseAlarmRate 0.4 ^ 
-precalcValBufSize 4096 ^

-precalcIdxBufSize 4096


