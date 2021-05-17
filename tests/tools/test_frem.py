import re
import shutil
from io import StringIO

import numpy as np
import pandas as pd
import pytest
from pytest import approx

import pharmpy.modeling as modeling
from pharmpy import Model
from pharmpy.tools.common import create_results
from pharmpy.tools.frem.models import calculate_parcov_inits, create_model3b
from pharmpy.tools.frem.results import (
    calculate_results,
    calculate_results_using_bipp,
    get_params,
    psn_frem_results,
)
from pharmpy.tools.frem.tool import check_covariates


def test_check_covariates(testdata):
    model = Model(testdata / 'nonmem' / 'pheno_real.mod')
    newcov = check_covariates(model, ['WGT', 'APGR'])
    assert newcov == ['WGT', 'APGR']
    newcov = check_covariates(model, ['APGR', 'WGT'])
    assert newcov == ['APGR', 'WGT']
    data = model.dataset
    data['NEW'] = data['WGT']
    model.dataset = data
    with pytest.warns(UserWarning):
        newcov = check_covariates(model, ['APGR', 'WGT', 'NEW'])
    assert newcov == ['APGR', 'WGT']
    with pytest.warns(UserWarning):
        newcov = check_covariates(model, ['NEW', 'APGR', 'WGT'])
    assert newcov == ['NEW', 'APGR']


@pytest.mark.filterwarnings("ignore::UserWarning")
def test_check_covariates_mult_warns(testdata):
    # These are separated because capturing the warnings did not work.
    # Possibly because more than one warning is issued
    model = Model(testdata / 'nonmem' / 'pheno_real.mod')
    newcov = check_covariates(model, ['FA1', 'FA2'])
    assert newcov == []


def test_parcov_inits(testdata):
    model = Model(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_3.mod')
    params = calculate_parcov_inits(model, 2)
    assert params == approx(
        {
            'OMEGA(3,1)': 0.02560327,
            'OMEGA(3,2)': -0.001618381,
            'OMEGA(4,1)': -0.06764814,
            'OMEGA(4,2)': 0.02350935,
        }
    )


def test_create_model3b(testdata):
    model3 = Model(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_3.mod')
    model1b = Model(testdata / 'nonmem' / 'pheno_real.mod')
    model3b = create_model3b(model1b, model3, 2)
    pset = model3b.parameters
    assert pset['OMEGA(3,1)'].init == approx(0.02560327)
    assert pset['THETA(1)'].init == 0.00469555
    assert model3b.name == 'model_3b'


def test_bipp_covariance(testdata):
    model = Model(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_4.mod')
    np.random.seed(9532)
    res = calculate_results_using_bipp(model, continuous=['APGR', 'WGT'], categorical=[])
    assert res


def test_frem_results_pheno(testdata):
    model = Model(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_4.mod')
    rng = np.random.default_rng(39)
    res = calculate_results(model, continuous=['APGR', 'WGT'], categorical=[], samples=10, seed=rng)

    correct = """parameter,covariate,condition,p5,mean,p95
CL,APGR,5th,0.972200,1.099294,1.242870
CL,APGR,95th,0.901919,0.958505,1.013679
CL,WGT,5th,0.864055,0.941833,1.003508
CL,WGT,95th,0.993823,1.138392,1.346290
V,APGR,5th,0.818275,0.900856,0.980333
V,APGR,95th,1.009562,1.052237,1.099986
V,WGT,5th,0.957804,0.994109,1.030915
V,WGT,95th,0.940506,1.014065,1.091648
"""

    correct = pd.read_csv(StringIO(correct), index_col=[0, 1, 2])
    correct.index.set_names(['parameter', 'covariate', 'condition'], inplace=True)
    pd.testing.assert_frame_equal(res.covariate_effects, correct)

    correct = """ID,parameter,observed,p5,p95
1.0,CL,0.9747876089262426,0.9623876223423867,0.9824852674876945
1.0,V,1.0220100411225312,1.0023922181039566,1.0210291755653986
2.0,CL,0.9322191565835464,0.879772943050749,0.9870177704564436
2.0,V,1.0863063389527468,1.0106054760663574,1.0949107930978257
3.0,CL,1.0091536521780653,0.9983634898455471,1.018968935499065
3.0,V,0.9872706260693193,0.9844268334767777,0.9985306191354839
4.0,CL,0.9606207744865287,0.8966200610185175,0.9788305801683045
4.0,V,1.0035010263500566,0.9663822687437207,1.0253995817536679
5.0,CL,0.9747876089262426,0.9623876223423867,0.9824852674876945
5.0,V,1.0220100411225312,1.0023922181039566,1.0210291755653986
6.0,CL,1.0109608882054792,0.95675167702286,1.047032014139463
6.0,V,0.9641361555839656,0.9426547826305651,0.9971274446069774
7.0,CL,0.9944873258008428,0.9234085517155061,1.0329306928525204
7.0,V,0.9693908196899773,0.9377215638220676,1.005787746465714
8.0,CL,0.958903488487699,0.9297581756071042,0.9698533840376546
8.0,V,1.0275801252314685,0.9995096153857336,1.0305284160928718
9.0,CL,0.9493585916770979,0.9168219777534304,0.9781229378966473
9.0,V,1.0551004552760428,1.0074271830514618,1.0558192686142556
10.0,CL,0.9747876089262426,0.9623876223423867,0.9824852674876945
10.0,V,1.0220100411225312,1.0023922181039566,1.0210291755653986
11.0,CL,0.958903488487699,0.9297581756071042,0.9698533840376546
11.0,V,1.0275801252314685,0.9995096153857336,1.0305284160928718
12.0,CL,0.9927094983849412,0.964423399504378,1.0049743061538365
12.0,V,0.9926513892731682,0.9792468738482092,1.0050990195407465
13.0,CL,0.976533341560172,0.9298917166331006,0.9915919601050044
13.0,V,0.9980614650127685,0.9734701845573707,1.014970713377564
14.0,CL,0.951058782653966,0.9134209062993411,0.9640823778650414
14.0,V,1.0303765312253497,0.9980598360399148,1.0355596311429953
15.0,CL,0.9668129564881183,0.946396890356916,0.9756598929662376
15.0,V,1.0247912889635773,1.0009493481389617,1.0255263136231711
16.0,CL,0.9095265185860849,0.8596675559459472,0.9496967076081981
16.0,V,1.0951991931031655,1.0132776214955752,1.0943338294249254
17.0,CL,1.0026902472906303,0.9399291242693675,1.0399572629061364
17.0,V,0.9667599267916591,0.9401828423267352,1.0008887085836748
18.0,CL,0.9944873258008428,0.9234085517155061,1.0329306928525204
18.0,V,0.9693908196899773,0.9377215638220676,1.005787746465714
19.0,CL,1.1053968956987084,0.9550940894449401,1.252630489586505
19.0,V,0.8533833334063132,0.8137505765058551,0.9831214378016516
20.0,CL,0.9845882285317421,0.946997120743552,0.9982223740073822
20.0,V,0.9953527419235736,0.9766736357263162,1.0100205095501023
21.0,CL,1.0073495639382477,0.9911227412088595,1.044387148904489
21.0,V,1.010960288562291,0.9946666839380782,1.0280977419525212
22.0,CL,0.95718931798836,0.9239134454923038,0.990767474177394
22.0,V,1.0522369332956463,1.0065490452129744,1.056769129368429
23.0,CL,1.2458833674993706,1.174095979524402,1.4471022995695604
23.0,V,0.8590844344554049,0.8511772373661953,0.9978047397479437
24.0,CL,1.2898066624107463,1.2042629850784445,1.5119655998604768
24.0,V,0.8298831532047879,0.8263339770363893,0.9920863584513262
25.0,CL,1.078488455291716,0.9098851631064538,1.225407606892303
25.0,V,0.8603694590532166,0.8074080480904899,0.9856154957740352
26.0,CL,1.098674754163057,1.0106076147912186,1.391954855775848
26.0,V,1.0288378820849053,0.9418188471476597,1.1554219798982115
27.0,CL,1.070797186680841,1.0497848923764674,1.1095595928316735
27.0,V,0.9459681173444604,0.9476795247485684,0.9950741922847095
28.0,CL,1.0719298253304665,0.9904819562406533,1.3176274576021954
28.0,V,1.03726038617135,0.9555429217552073,1.1460077037451706
29.0,CL,0.9432781990804444,0.8973792501310945,0.9583465711235544
29.0,V,1.033180567003963,0.9960458633951124,1.040714440250996
30.0,CL,0.9810711118911185,0.9449009310699679,1.0344015681825607
30.0,V,1.0436929362812277,1.0039329214277344,1.0652073284592802
31.0,CL,0.9493585916770979,0.9168219777534304,0.9781229378966473
31.0,V,1.0551004552760428,1.0074271830514618,1.0558192686142556
32.0,CL,1.107736990310448,1.017366137348099,1.4176689131640372
32.0,V,1.0260456715775965,0.9372967141871299,1.158587315986331
33.0,CL,0.9730450546630892,0.9382619333344786,1.0165736891038182
33.0,V,1.0465331908863182,1.0048019204607868,1.0623824400913477
34.0,CL,1.0815633528084572,1.0321958697700877,1.1412768058833191
34.0,V,0.9212939726059592,0.9200323034240248,0.988963216508514
35.0,CL,1.1248963316842946,1.0896346701791253,1.2343223846182518
35.0,V,0.930668271710216,0.9207989580569778,1.003672734199572
36.0,CL,1.0361843083002586,1.00221039689929,1.0701140338462605
36.0,V,0.9563075137562995,0.9501349320058959,0.9945680777536055
37.0,CL,0.9095265185860849,0.8596675559459472,0.9496967076081981
37.0,V,1.0951991931031655,1.0132776214955752,1.0943338294249254
38.0,CL,0.941591971811965,0.9097851719695764,0.9656476681586792
38.0,V,1.057971753742054,1.008294200694932,1.0570460812274063
39.0,CL,0.9382282786328352,0.863978786528425,1.035323710460379
39.0,V,1.1093533335978631,1.0111358019986683,1.1465425834388718
40.0,CL,1.0571250130931833,0.9581487136615587,1.1444659341348051
40.0,V,0.9070708069040182,0.8758299821223936,0.9900800887894693
41.0,CL,0.999108524985206,0.9844282618752698,1.0258297357380268
41.0,V,1.0137114661503888,0.9995253738170382,1.0253723417738896
42.0,CL,1.0372807133026336,0.9639930739237731,1.2247756092969586
42.0,V,1.048597477200077,0.9742146897963039,1.133644558392112
43.0,CL,1.0963536766193422,0.942906018662724,1.2430275278873713
43.0,V,0.8557057052065501,0.8116272866638132,0.9839498555735701
44.0,CL,0.9747876089262426,0.9623876223423867,0.9824852674876945
44.0,V,1.0220100411225312,1.0023922181039566,1.0210291755653986
45.0,CL,1.059017894749882,0.9172185488462667,1.1761347712395736
45.0,V,0.8858157120486193,0.838722698055201,0.9886853338113423
46.0,CL,0.9262487191851418,0.8897940034550293,0.9468609378746285
46.0,V,1.0637378541056135,1.0053811001126487,1.0618091096304203
47.0,CL,1.0203778571306483,0.9510168403689275,1.1808779605388167
47.0,V,1.0543126075153102,0.9837140275640088,1.1275426462036497
48.0,CL,0.8963081434656491,0.8289037114264994,0.923248384252418
48.0,V,1.0753645249641806,0.9995929717263163,1.0823351064416151
49.0,CL,0.941591971811965,0.9097851719695764,0.9656476681586792
49.0,V,1.057971753742054,1.008294200694932,1.0570460812274063
50.0,CL,0.976533341560172,0.9298917166331006,0.9915919601050044
50.0,V,0.9980614650127685,0.9734701845573707,1.014970713377564
51.0,CL,0.887386262989466,0.8348776008389295,0.9195007177004489
51.0,V,1.104164853369307,1.0098626419201524,1.0995841187514204
52.0,CL,0.9355612682293925,0.8816278276092833,0.9526457840151445
52.0,V,1.0359922336014173,0.9925407119469869,1.0463332767905136
53.0,CL,0.9730450546630892,0.9382619333344786,1.0165736891038182
53.0,V,1.0465331908863182,1.0048019204607868,1.0623824400913477
54.0,CL,0.9810711118911185,0.9449009310699679,1.0344015681825607
54.0,V,1.0436929362812277,1.0039329214277344,1.0652073284592802
55.0,CL,1.0295480825430916,0.9489431971840638,1.0908624641438185
55.0,V,0.9364397440565791,0.9074358325804165,0.9940178908810062
56.0,CL,0.9881180733519868,0.868368787557875,1.0544960994592296
56.0,V,0.9492512613562971,0.8956645356453113,1.0114121853036042
57.0,CL,1.060138503325679,1.043458933657303,1.1198727965741848
57.0,V,0.9713027400777485,0.9613644126949645,1.009755277835067
58.0,CL,0.9493585916770979,0.9168219777534304,0.9781229378966473
58.0,V,1.0551004552760428,1.0074271830514618,1.0558192686142556
59.0,CL,0.976533341560172,0.9298917166331006,0.9915919601050044
59.0,V,0.9980614650127685,0.9734701845573707,1.014970713377564
"""
    correct = pd.read_csv(StringIO(correct), index_col=[0, 1])
    correct.index.set_names(['ID', 'parameter'], inplace=True)
    pd.testing.assert_frame_equal(res.individual_effects, correct)

    correct = """parameter,covariate,sd_observed,sd_5th,sd_95th
CL,none,0.19836380718266122,0.10698386364464521,0.22813605494479994
CL,APGR,0.1932828383897819,0.08207800471169897,0.22738951605057137
CL,WGT,0.19363776172900196,0.10259365732821585,0.19906614312476859
CL,all,0.1851006246151042,0.06925915743342524,0.1897192131955216
V,none,0.16105092362355455,0.12600993671999713,0.18079489759700668
V,APGR,0.1468832868065463,0.11406607129463658,0.1704182899316319
V,WGT,0.16104200315990183,0.12203994522797203,0.18040105423522765
V,all,0.14572521381314374,0.11146577839548052,0.16976758171177983
"""
    correct = pd.read_csv(StringIO(correct), index_col=[0, 1])
    correct.index.set_names(['parameter', 'covariate'], inplace=True)
    pd.testing.assert_frame_equal(res.unexplained_variability, correct)

    correct = pd.DataFrame(
        {
            'p5': [1.0, 0.7],
            'mean': [6.423729, 1.525424],
            'p95': [9.0, 3.2],
            'stdev': [2.237636, 0.704565],
            'ref': [6.423729, 1.525424],
            'categorical': [False, False],
            'other': [np.nan, np.nan],
        },
        index=['APGR', 'WGT'],
    )
    correct.index.name = 'covariate'
    pd.testing.assert_frame_equal(res.covariate_statistics, correct)

    res.add_plots()


def test_frem_results_pheno_categorical(testdata):
    model = Model(testdata / 'nonmem' / 'frem' / 'pheno_cat' / 'model_4.mod')
    rng = np.random.default_rng(8978)
    res = calculate_results(model, continuous=['WGT'], categorical=['APGRX'], samples=10, seed=rng)

    correct = """parameter,covariate,condition,p5,mean,p95
CL,WGT,5th,0.8819981232638212,0.921855097970373,0.9914329783724809
CL,WGT,95th,1.0205945064659645,1.185488698855152,1.290159192560782
CL,APGRX,other,0.9896891119555906,1.075199179067876,1.1807700140470523
V,WGT,5th,0.964309799914709,0.9985868417769049,1.035226303298895
V,WGT,95th,0.9326778994009551,1.0046966129187815,1.0765572970209067
V,APGRX,other,0.8525465875034259,0.9122600523096345,0.9815632076342711
"""

    correct = pd.read_csv(StringIO(correct), index_col=[0, 1, 2])
    correct.index.set_names(['parameter', 'covariate', 'condition'], inplace=True)
    pd.testing.assert_frame_equal(res.covariate_effects, correct)

    correct = """ID,parameter,observed,p5,p95
1.0,CL,0.9912884661387944,0.9813048663781488,0.9973390660104855
1.0,V,1.0011657907076288,0.9961479855124891,1.005111329256977
2.0,CL,0.9982280031437448,0.996181881537249,0.9994567821564067
2.0,V,1.0002361858019588,0.9992179070508342,1.0010337253846464
3.0,CL,0.9982280031437448,0.996181881537249,0.9994567821564067
3.0,V,1.0002361858019588,0.9992179070508342,1.0010337253846464
4.0,CL,0.9573077718907862,0.910188324169257,0.9871990321851049
4.0,V,1.0058267874330078,0.9809464793215863,1.0257787028045986
5.0,CL,0.9912884661387944,0.9813048663781488,0.9973390660104855
5.0,V,1.0011657907076288,0.9961479855124891,1.005111329256977
6.0,CL,1.1198435491217265,0.9459948274061026,1.1635334496132532
6.0,V,0.9085976422437901,0.849396189143409,0.9840276246988151
7.0,CL,1.1043277095093798,0.9254636049571561,1.1416220891599078
7.0,V,0.9102872994311817,0.8463653396009687,0.9885208818121852
8.0,CL,0.9775538039511688,0.9522143934071415,0.9931939403631005
8.0,V,1.0030275905796406,0.9900378689946755,1.0133221269461574
9.0,CL,0.9912884661387944,0.9813048663781488,0.9973390660104855
9.0,V,1.0011657907076288,0.9961479855124891,1.005111329256977
10.0,CL,0.9912884661387944,0.9813048663781488,0.9973390660104855
10.0,V,1.0011657907076288,0.9961479855124891,1.005111329256977
11.0,CL,0.9775538039511688,0.9522143934071415,0.9931939403631005
11.0,V,1.0030275905796406,0.9900378689946755,1.0133221269461574
12.0,CL,0.984397205662633,0.9666502028409082,0.9952515267976471
12.0,V,1.0020962549833665,0.9930879961614127,1.0092074166446894
13.0,CL,0.9707579766809108,0.9379942690835713,0.9911661238967686
13.0,V,1.0039597917474488,0.9869975923396912,1.0174555221050898
14.0,CL,0.9707580846524858,0.9379944014878209,0.991166185846897
14.0,V,1.0039597398327802,0.9869975601129544,1.0174554559295954
15.0,CL,0.984397205662633,0.9666502028409082,0.9952515267976471
15.0,V,1.0020962549833665,0.9930879961614127,1.0092074166446894
16.0,CL,0.9775538039511688,0.9522143934071415,0.9931939403631005
16.0,V,1.0030275905796406,0.9900378689946755,1.0133221269461574
17.0,CL,1.112058541995997,0.9356706165665988,1.152524292807003
17.0,V,0.9094420814108902,0.8478792682090651,0.986271656447999
18.0,CL,1.1043277095093798,0.9254636049571561,1.1416220891599078
18.0,V,0.9102872994311817,0.8463653396009687,0.9885208818121852
19.0,CL,1.1043277095093798,0.9254636049571561,1.1416220891599078
19.0,V,0.9102872994311817,0.8463653396009687,0.9885208818121852
20.0,CL,0.9775538039511688,0.9522143934071415,0.9931939403631005
20.0,V,1.0030275905796406,0.9900378689946755,1.0133221269461574
21.0,CL,1.0193394191110992,1.00599293540612,1.0421805062160383
21.0,V,0.9974525520566727,0.9889110630256354,1.0084874924609004
22.0,CL,0.9982280031437448,0.996181881537249,0.9994567821564067
22.0,V,1.0002361858019588,0.9992179070508342,1.0010337253846464
23.0,CL,1.278561145560325,1.0730798901918503,1.4670001204876155
23.0,V,0.8927014996056475,0.830129260250684,0.9677376453087094
24.0,CL,1.2875116337804728,1.0760208287968924,1.486022079679879
24.0,V,0.8918726161520479,0.8274821274377496,0.9703490058424948
25.0,CL,1.0814559146197718,0.8955313272421234,1.1140394348719436
25.0,V,0.9128276994620532,0.8418413279494222,0.995300017307435
26.0,CL,1.1476875524497763,1.0484678801415581,1.3459916649832033
26.0,V,0.9818242876491968,0.9232323698131256,1.0627513938695634
27.0,CL,1.175885957445256,1.0197164262951008,1.2622252762813193
27.0,V,0.9027084993825373,0.855964580433165,0.968464288047712
28.0,CL,1.1239176188679145,1.0402745719548487,1.2865757863940388
28.0,V,0.9845643436557832,0.9344603555527986,1.0529567054182085
29.0,CL,0.9640094405028626,0.9239867037463769,0.9891678953609051
29.0,V,1.0048928527141423,0.9839671543617752,1.021607664000325
30.0,CL,1.0193394191110992,1.00599293540612,1.0421805062160383
30.0,V,0.9974525520566727,0.9889110630256354,1.0084874924609004
31.0,CL,0.9912884661387944,0.9813048663781488,0.9973390660104855
31.0,V,1.0011657907076288,0.9961479855124891,1.005111329256977
32.0,CL,1.1557218681759203,1.05126810152679,1.366400391618407
32.0,V,0.9809126526774464,0.9195233237879691,1.0660374567314548
33.0,CL,1.0122531534168406,1.0037835182166013,1.026616284417212
33.0,V,0.9983795653196571,0.9929336729389665,1.0053876334203307
34.0,CL,1.1595936298853569,0.9983974414829697,1.2311278678037307
34.0,V,0.9043872049318215,0.8570257176683481,0.972885211173309
35.0,CL,1.2261492360260002,1.0562723405206516,1.3604180326658308
35.0,V,0.8976910613647905,0.8462803764546969,0.9613889846545988
36.0,CL,1.1435270215868598,0.9775429514593513,1.2008124091644
36.0,V,0.9060690340346341,0.8539648908820485,0.9773266842311321
37.0,CL,0.9775538039511688,0.9522143934071415,0.9931939403631005
37.0,V,1.0030275905796406,0.9900378689946755,1.0133221269461574
38.0,CL,0.984397205662633,0.9666502028409082,0.9952515267976471
38.0,V,1.0020962549833665,0.9930879961614127,1.0092074166446894
39.0,CL,1.026475342573432,1.0082333483688481,1.057980920687581
39.0,V,0.9965263930197235,0.9849065719793645,1.011597425168051
40.0,CL,1.112058541995997,0.9356706165665988,1.152524292807003
40.0,V,0.9094420814108902,0.8478792682090651,0.986271656447999
41.0,CL,1.0122531534168406,1.0037835182166013,1.026616284417212
41.0,V,0.9983795653196571,0.9929336729389665,1.0053876334203307
42.0,CL,1.0929891262425546,1.029825992792653,1.2114179127546956
42.0,V,0.9882295642803754,0.9496684028378504,1.0400447974474016
43.0,CL,1.0966505664884518,0.9153722750925393,1.1308256235685081
43.0,V,0.9111333089443203,0.8448543757160204,0.9907753447791341
44.0,CL,0.9912884661387944,0.9813048663781488,0.9973390660104855
44.0,V,1.0011657907076288,0.9961479855124891,1.005111329256977
45.0,CL,1.0890265798617313,0.9053950626054712,1.1201336226344416
45.0,V,0.911980128603927,0.843346338517983,0.9930351056003389
46.0,CL,0.9707579766809108,0.9379942690835713,0.9911661238967686
46.0,V,1.0039597917474488,0.9869975923396912,1.0174555221050898
47.0,CL,1.0778449935823065,1.0248012335579348,1.1755013302099169
47.0,V,0.990067352893127,0.9573760842928019,1.033651139901418
48.0,CL,0.9440437853762491,0.8832067666804916,0.9833486480091203
48.0,V,1.0076972748297237,0.9749343084168995,1.034177812011554
49.0,CL,0.984397205662633,0.9666502028409082,0.9952515267976471
49.0,V,1.0020962549833665,0.9930879961614127,1.0092074166446894
50.0,CL,0.9707579766809108,0.9379942690835713,0.9911661238967686
50.0,V,1.0039597917474488,0.9869975923396912,1.0174555221050898
51.0,CL,0.9573077718907862,0.910188324169257,0.9871990321851049
51.0,V,1.0058267874330078,0.9809464793215863,1.0257787028045986
52.0,CL,0.9573077718907862,0.910188324169257,0.9871990321851049
52.0,V,1.0058267874330078,0.9809464793215863,1.0257787028045986
53.0,CL,1.0122531534168406,1.0037835182166013,1.026616284417212
53.0,V,0.9983795653196571,0.9929336729389665,1.0053876334203307
54.0,CL,1.0193394191110992,1.00599293540612,1.0421805062160383
54.0,V,0.9974525520566727,0.9889110630256354,1.0084874924609004
55.0,CL,1.112058541995997,0.9356706165665988,1.152524292807003
55.0,V,0.9094420814108902,0.8478792682090651,0.986271656447999
56.0,CL,1.073937878921724,0.8857793202519842,1.1085507751714088
56.0,V,0.9136760580307196,0.8403392739705754,0.9975701876968037
57.0,CL,1.0408973539422075,1.0128079308219036,1.090304270867253
57.0,V,0.9946766605413693,0.9769517079786997,1.0178475600710417
58.0,CL,0.9912884661387944,0.9813048663781488,0.9973390660104855
58.0,V,1.0011657907076288,0.9961479855124891,1.005111329256977
59.0,CL,0.9707579766809108,0.9379942690835713,0.9911661238967686
59.0,V,1.0039597917474488,0.9869975923396912,1.0174555221050898
"""
    correct = pd.read_csv(StringIO(correct), index_col=[0, 1])
    correct.index.set_names(['ID', 'parameter'], inplace=True)
    pd.testing.assert_frame_equal(res.individual_effects, correct)

    correct = """parameter,covariate,sd_observed,sd_5th,sd_95th
CL,none,0.18764141333937986,0.09771861614594449,0.23156758822583026
CL,WGT,0.18248555852725476,0.07670351148747996,0.21589015217788352
CL,APGRX,0.17859851761700796,0.09431920743811947,0.22928965406476434
CL,all,0.17186720148456744,0.07223904432988808,0.2136863363112255
V,none,0.15093077883586237,0.13983739042307936,0.16722064689152502
V,WGT,0.15090452947915595,0.13939517671288412,0.16629069485220008
V,APGRX,0.14429826722004974,0.13207359729044602,0.16582931550214622
V,all,0.1441532460182698,0.1294082747127788,0.16527164471815176
"""

    correct = pd.read_csv(StringIO(correct), index_col=[0, 1])
    correct.index.set_names(['parameter', 'covariate'], inplace=True)
    pd.testing.assert_frame_equal(res.unexplained_variability, correct)

    correct = pd.DataFrame(
        {
            'p5': [0.7, 0],
            'mean': [1.525424, 0.711864],
            'p95': [3.2, 1],
            'stdev': [0.704565, 0.456782],
            'ref': [1.525424, 1.0],
            'categorical': [False, True],
            'other': [np.nan, 0],
        },
        index=['WGT', 'APGRX'],
    )
    correct.index.name = 'covariate'
    pd.testing.assert_frame_equal(res.covariate_statistics, correct)


def test_get_params(testdata):
    model_frem = Model(testdata / 'nonmem' / 'frem' / 'pheno' / 'model_4.mod')
    rvs, _ = model_frem.random_variables.etas.distributions()[-1]
    npars = 2

    param_names = get_params(model_frem, rvs, npars)
    assert param_names == ['CL', 'V']

    model_multiple_etas = re.sub(
        r'(V=TVV\*EXP\(ETA\(2\)\))',
        r'\1*EXP(ETA(3))',
        str(model_frem),
    )

    model = Model(StringIO(model_multiple_etas))
    model.dataset = model_frem.dataset
    rvs, _ = model.random_variables.etas.distributions()[-1]
    npars = 3

    param_names = get_params(model, rvs, npars)
    assert param_names == ['CL', 'V(1)', 'V(2)']

    model_separate_declare = re.sub(
        r'(V=TVV\*EXP\(ETA\(2\)\))',
        'ETA2=ETA(2)\n      V=TVV*EXP(ETA2)',
        str(model_frem),
    )

    model = Model(StringIO(model_separate_declare))
    model.dataset = model_frem.dataset
    rvs, _ = model.random_variables.etas.distributions()[-1]
    npars = 2

    param_names = get_params(model, rvs, npars)
    print(param_names)
    assert param_names == ['CL', 'V']


def test_psn_frem_results(testdata):
    res = psn_frem_results(testdata / 'psn' / 'frem_dir1', method='bipp')
    ofv = res.ofv['ofv']
    assert len(ofv) == 5
    assert ofv['model_1'] == approx(730.894727)
    assert ofv['model_2'] == approx(896.974324)
    assert ofv['model_3'] == approx(868.657803)
    assert ofv['model_3b'] == approx(852.803483)
    assert ofv['model_4'] == approx(753.302743)

    correct = """model type		THETA(1)  THETA(2)  OMEGA(1,1)  OMEGA(2,1)  OMEGA(2,2)  OMEGA(3,1)  OMEGA(3,2)  OMEGA(3,3)  OMEGA(4,1)  OMEGA(4,2)  OMEGA(4,3)  OMEGA(4,4)  SIGMA(1,1)
model_1  init      0.004693   1.00916    0.030963         NaN    0.031128         NaN         NaN         NaN         NaN         NaN         NaN         NaN    0.013241
model_1  estimate  0.005818   1.44555    0.111053         NaN    0.201526         NaN         NaN         NaN         NaN         NaN         NaN         NaN    0.016418
model_2  init           NaN       NaN         NaN         NaN         NaN         NaN         NaN    1.000000         NaN         NaN    0.244579    1.000000         NaN
model_2  estimate       NaN       NaN         NaN         NaN         NaN         NaN         NaN    1.000000         NaN         NaN    0.244579    1.000000         NaN
model_3  init           NaN       NaN    0.115195    0.007066    0.209016   -0.010583    0.107027    1.000008    0.171529    0.404278    0.244448    1.002173         NaN
model_3  estimate       NaN       NaN    0.115195    0.007066    0.209016   -0.010583    0.107027    1.000010    0.171529    0.404278    0.244448    1.002170         NaN
model_3b init      0.005818   1.44555    0.125999    0.020191    0.224959   -0.012042    0.115427    1.000032    0.208475    0.415588    0.244080    1.007763    0.016418
model_3b estimate  0.005818   1.44555    0.126000    0.020191    0.224959   -0.012042    0.115427    1.000030    0.208475    0.415588    0.244080    1.007760    0.016418
model_4  init      0.005818   1.44555    0.126000    0.020191    0.224959   -0.012042    0.115427    1.000030    0.208475    0.415588    0.244080    1.007760    0.016418
model_4  estimate  0.007084   1.38635    0.220463    0.195326    0.176796    0.062712    0.117271    1.039930    0.446939    0.402075    0.249237    1.034610    0.015250
"""  # noqa E501
    correct = pd.read_csv(StringIO(correct), index_col=[0, 1], delim_whitespace=True)
    pd.testing.assert_frame_equal(res.parameter_inits_and_estimates, correct, rtol=1e-4)

    pc = res.base_parameter_change
    assert len(pc) == 5
    assert pc['THETA(1)'] == 21.77321763763502
    assert pc['THETA(2)'] == -4.095327038151563
    assert pc['OMEGA(1,1)'] == pytest.approx(98.52052623522104, abs=1e-12)
    assert pc['OMEGA(2,2)'] == -12.271369451088198
    assert pc['SIGMA(1,1)'] == pytest.approx(-7.110618417927009, abs=1e-12)

    correct = """,mean,stdev
APGR,6.42372,2.237640
WGT,1.525424,0.704565
"""
    correct = pd.read_csv(StringIO(correct), index_col=[0])
    pd.testing.assert_frame_equal(res.estimated_covariates, correct, rtol=1e-5)

    correct = """condition,parameter,CL,V
all,CL,0.025328,0.022571
all,V,0.022571,0.020115
APGR,CL,0.216681,0.188254
APGR,V,0.188254,0.163572
WGT,CL,0.027391,0.021634
WGT,V,0.021634,0.020540
"""
    correct = pd.read_csv(StringIO(correct), index_col=[0, 1])
    pd.testing.assert_frame_equal(res.parameter_variability, correct, rtol=1e-4)

    correct = """condition,parameter,APGR,WGT
all,CL,-0.020503,0.628814
all,V,0.00930905,0.544459
each,CL,0.0269498,0.613127
each,V,0.0503961,0.551581
"""

    correct = pd.read_csv(StringIO(correct), index_col=[0, 1])
    pd.testing.assert_frame_equal(res.coefficients, correct, rtol=1e-5)


def test_create_results(testdata):
    res = create_results(testdata / 'psn' / 'frem_dir1', method='bipp')
    ofv = res.ofv['ofv']
    assert len(ofv) == 5


def test_modeling_create_results(testdata):
    res = modeling.create_results(testdata / 'psn' / 'frem_dir1', method='bipp')
    ofv = res.ofv['ofv']
    assert len(ofv) == 5


def test_create_report(testdata, tmp_path):
    res = modeling.read_results(testdata / 'frem' / 'results.json')
    shutil.copy(testdata / 'frem' / 'results.json', tmp_path)
    res.create_report(tmp_path)
    html = tmp_path / 'results.html'
    assert html.is_file()
    assert html.stat().st_size > 500000
