$PROBLEM PHENOBARB SIMPLE MODEL
$DATA ../pheno.dta IGNORE=@
$INPUT ID TIME AMT WGT APGR DV FA1 FA2
$SUBROUTINE ADVAN5 TRANS1
$MODEL COMP=(A DEFDOSE) COMP=(B) COMP=(C) COMP=(D) COMP=(CENTRAL) COMP=(E)

$PK
IF(AMT.GT.0) BTIME=TIME
TAD=TIME-BTIME
TVCL=THETA(1)*WGT
TVV=THETA(2)*WGT
IF(APGR.LT.5) TVV=TVV*(1+THETA(3))
CL=TVCL*EXP(ETA(1))
V=TVV*EXP(ETA(2))
K=CL/V
KA=THETA(6)
K12 = THETA(4)
K23 = THETA(5)
K34 = KA
K45 = THETA(7)
K56 = THETA(8)
K64 = THETA(9)
K50 = K
S1 = V

$ERROR
W=F
Y=F+W*EPS(1)
IPRED=F
IRES=DV-IPRED
IWRES=IRES/W

$THETA (0,0.00469307) ; POP_CL
$THETA (0,1.00916) ; POP_V
$THETA (-.99,.1)
$THETA (0,10)
$THETA (0,10)
$THETA (0,10)
$THETA (0,10)
$THETA (0,10)
$THETA (0,10)
$OMEGA DIAGONAL(2)
 0.0309626  ;       IVCL
 0.031128  ;        IVV

$SIGMA 1e-7
$ESTIMATION METHOD=1 INTERACTION
$COVARIANCE UNCONDITIONAL
$TABLE ID TIME DV AMT WGT APGR IPRED PRED RES TAD CWRES NPDE NOAPPEND
       NOPRINT ONEHEADER FILE=sdtab1
