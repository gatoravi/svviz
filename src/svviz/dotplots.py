import logging
import os
import shutil
import subprocess
import tempfile

try:
    import numpy
    from scipy import misc

    def dotplot2(s1, s2, wordsize=5, overlap=5, verbose=1):
        """ verbose = 0 (no progress), 1 (progress if s1 and s2 are long) or
        2 (progress in any case) """
        doProgress = False
        if verbose > 1 or len(s1)*len(s2) > 1e6:
            doProgress = True

        mat = numpy.ones(((len(s1)-wordsize)/overlap+2, (len(s2)-wordsize)/overlap+2))

        for i in range(0, len(s1)-wordsize, overlap):
            if i % 1000 == 0 and doProgress:
                logging.info("  dotplot progress: {} of {} rows done".format(i, len(s1)-wordsize))
            word1 = s1[i:i+wordsize]

            for j in range(0, len(s2)-wordsize, overlap):
                word2 = s2[j:j+wordsize]

                if word1 == word2 or word1 == word2[::-1]:
                    mat[i/overlap, j/overlap] = 0
        
        imgData = None
        tempDir = tempfile.mkdtemp()
        try:
            path = os.path.join(tempDir, "dotplot.png")
            misc.imsave(path, mat)
            imgData = open(path).read()
        except Exception, e:
            logging.error("Error generating dotplots:'{}'".format(e))
        finally:
            shutil.rmtree(tempDir)
        return imgData

except ImportError:
    def dotplot2(*args, **kwdargs):
        logging.error("dotplots requires the python libraries scipy and PIL")
        return None


def yass_dotplot(s1, breakpoints):
    from rpy2 import robjects as ro

    length = len(s1)

    tempDir = tempfile.mkdtemp()

    tempFasta = os.path.join(tempDir, "seq.fa")
    tempYASSResult = os.path.join(tempDir, "result.txt")
    tempPNG = os.path.join(tempDir, "result.png")

    tempFastaFile = open(tempFasta, "w")
    tempFastaFile.write(">seq\n{}".format(s1))
    tempFastaFile.close()

    proc = subprocess.Popen("yass -d 3 -o {} {}".format(tempYASSResult, tempFasta), shell=True,
        stderr=subprocess.PIPE)
    resultCode = proc.wait()
    if resultCode != 0:
        raise Exception("Check that yass is installed correctly")
    stderr = proc.stderr.readlines()
    if "Error" in stderr[0]:
        print "Error running yass: '{}'".format(stderr[0])
        raise Exception("Error running yass")

    ro.r.png(tempPNG, res=150, width=1000, height=1000)
    ro.r.plot(ro.IntVector([0]), ro.IntVector([0]), type="n", xaxs="i", yaxs="i", 
              xlab="Position in reference allele", ylab="Position in reference allele",
              xlim=ro.IntVector([0,length]),
              ylim=ro.IntVector([0,length]))

    for line in open(tempYASSResult):
        if line.startswith("#"):continue
        res = line.strip().split()
        if float(res[-1]) < 0.1:
            if res[6]=="f":
                ro.r.segments(int(res[0]), int(res[2]), int(res[1]), int(res[3]), col="blue", lwd=1)
            else:
                ro.r.segments(int(res[1]), int(res[2]), int(res[0]), int(res[3]), col="red", lwd=1)

    for breakpoint in breakpoints:
        ro.r.abline(h=breakpoint, lty=2, col="gray")
        ro.r.abline(v=breakpoint, lty=2, col="gray")

    ro.r["dev.off"]()

    return open(tempPNG).read()


def dotplot(dataHub):
    chromPart = list(dataHub.variant.chromParts("ref"))[0]
    ref = chromPart.getSeq()

    try:
        breakpoints = []
        curpos = 0
        for segment in chromPart.segments[:-1]:
            curpos += len(segment)
            breakpoints.append(curpos)

        return yass_dotplot(ref, breakpoints)
    except Exception, e:
        logging.info("  Couldn't run recommended dot-plot helper-program yass: '{}'".format(e))
        return dotplot2(ref, ref)


if __name__ == '__main__':
    import sys
    f = open(sys.argv[1])
    data = []
    for line in f:
        if line.startswith(">"):
            continue
        data.append(line.strip())
    s = "".join(data)
    print s[:5000]
    data = dotplot(s, s)
    open("temp.png", "wb").write(data)

    subprocess.call("open temp.png", shell=True)