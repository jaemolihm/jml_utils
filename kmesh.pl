#!/usr/bin/perl -w


$numargs = $#ARGV+1;

if (($numargs<3)||($numargs>4)) {
    print  "usage: n1 n2 n3 [wan]\n";
    print  "       n1  - divisions along 1st recip vector\n";
    print  "       n2  - divisions along 2nd recip vector\n";
    print  "       n3  - divisions along 3rd recip vector\n";
    print  "       wan - omit the kpoint weight (optional)\n";
    exit;
}

if ($ARGV[0]<=0) {
    print "n1 must be >0\n";
    exit;
}
if ($ARGV[1]<=0) {
    print "n2 must be >0\n";
    exit;
}
if ($ARGV[2]<=0) {
    print "n3 must be >0\n";
    exit;
}

$totpts=$ARGV[0]*$ARGV[1]*$ARGV[2];

if ($numargs==3) {
    print "K_POINTS crystal\n";
    print $totpts,"\n";
    for ($x=0; $x<$ARGV[0]; $x++) {
	for ($y=0; $y<$ARGV[1]; $y++) {
	    for ($z=0; $z<$ARGV[2]; $z++) {
		printf ("%16.12f%16.12f%16.12f%16.8e\n", $x/$ARGV[0],$y/$ARGV[1],$z/$ARGV[2],1/$totpts);
	    }
	}
    }
}


if ($numargs==4) {
    printf ("mp_grid = %6d %6d %6d\n", $ARGV[0], $ARGV[1], $ARGV[2]);
    printf ("begin kpoints\n");
    for ($x=0; $x<$ARGV[0]; $x++) {
	for ($y=0; $y<$ARGV[1]; $y++) {
	    for ($z=0; $z<$ARGV[2]; $z++) {
		printf ("%16.12f%16.12f%16.12f\n", $x/$ARGV[0],$y/$ARGV[1],$z/$ARGV[2]);
	    }
	}
    }
    printf ("end kpoints\n");
}


exit;
