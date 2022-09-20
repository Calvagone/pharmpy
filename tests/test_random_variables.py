import pickle

import pytest
import sympy
from sympy import Symbol as symbol

from pharmpy.model import (
    JointNormalDistribution,
    NormalDistribution,
    RandomVariables,
    VariabilityHierarchy,
    VariabilityLevel,
)


def test_normal_rv():
    dist = NormalDistribution.create('ETA(1)', 'iiv', 0, 1)
    assert dist.names == ('ETA(1)',)
    assert dist.level == 'IIV'
    dist = dist.derive(name='NEW')
    assert dist.names == ('NEW',)
    with pytest.raises(ValueError):
        NormalDistribution.create('X', 'iiv', 0, -1)


def test_joint_normal_rv():
    dist = JointNormalDistribution.create(['ETA(1)', 'ETA(2)'], 'iiv', [0, 0], [[1, 0.1], [0.1, 2]])
    assert dist.names == ('ETA(1)', 'ETA(2)')
    assert dist.level == 'IIV'
    dist = dist.derive(names=['NEW', 'ETA(2)'])
    assert dist.names == ('NEW', 'ETA(2)')
    with pytest.raises(ValueError):
        JointNormalDistribution.create(['ETA(1)', 'ETA(2)'], 'iiv', [0, 0], [[-1, 0.1], [0.1, 2]])


def test_eq_rv():
    dist1 = NormalDistribution.create('ETA(1)', 'iiv', 0, 1)
    dist2 = NormalDistribution.create('ETA(1)', 'iiv', 0, 1)
    assert dist1 == dist2
    dist3 = NormalDistribution.create('ETA(2)', 'iiv', 0, 1)
    assert dist1 != dist3
    dist4 = NormalDistribution.create('ETA(2)', 'iiv', 0, 0.1)
    assert dist3 != dist4


def test_empty_rvs():
    rvs = RandomVariables.create([])
    assert not rvs
    assert rvs.covariance_matrix == sympy.Matrix()


def test_repr_rv():
    dist1 = NormalDistribution.create('ETA(1)', 'iiv', 0, 1)
    assert repr(dist1) == 'ETA(1) ~ N(0, 1)'
    dist2 = JointNormalDistribution.create(
        ['ETA(1)', 'ETA(2)'], 'iiv', [0, 0], [[1, 0.1], [0.1, 2]]
    )
    assert (
        repr(dist2)
        == """⎡ETA(1)⎤    ⎧⎡0⎤  ⎡ 1   0.1⎤⎫
⎢      ⎥ ~ N⎪⎢ ⎥, ⎢        ⎥⎪
⎣ETA(2)⎦    ⎩⎣0⎦  ⎣0.1   2 ⎦⎭"""
    )


def test_repr_latex_rv():
    dist1 = JointNormalDistribution.create(['x', 'y'], 'iiv', [0, 0], [[1, 0.1], [0.1, 2]])
    assert (
        dist1._repr_latex_()
        == '$\\displaystyle \\left[\\begin{matrix}x\\\\y\\end{matrix}\\right]\\sim \\mathcal{N} \\left(\\displaystyle \\left[\\begin{matrix}0\\\\0\\end{matrix}\\right],\\displaystyle \\left[\\begin{matrix}1 & 0.1\\\\0.1 & 2\\end{matrix}\\right]\\right)$'  # noqa E501
    )

    dist2 = NormalDistribution.create('x', 'iiv', 0, 1)
    assert (
        dist2._repr_latex_()
        == '$\\displaystyle x\\sim  \\mathcal{N} \\left(\\displaystyle 0,\\displaystyle 1\\right)$'
    )


def test_parameters_rv():
    dist1 = NormalDistribution.create('ETA(2)', 'iiv', 0, symbol('OMEGA(2,2)'))
    assert dist1.parameter_names == ['OMEGA(2,2)']


def test_illegal_inits():
    with pytest.raises(TypeError):
        RandomVariables.create([8, 1])
    dist1 = NormalDistribution.create('ETA(1)', 'iiv', 0, 1)
    dist2 = NormalDistribution.create('ETA(1)', 'iiv', 0, 1)
    with pytest.raises(ValueError):
        RandomVariables.create([dist1, dist2])


def test_len():
    dist1 = NormalDistribution.create('ETA(1)', 'iiv', 0, 1)
    dist2 = NormalDistribution.create('ETA(2)', 'iiv', 0, 1)
    rvs = RandomVariables.create([dist1, dist2])
    assert len(rvs) == 2


def test_eq():
    dist1 = NormalDistribution.create('ETA(1)', 'iiv', 0, 1)
    dist2 = NormalDistribution.create('ETA(2)', 'iiv', 0, 1)
    dist3 = NormalDistribution.create('ETA(3)', 'iiv', 0, 1)
    rvs = RandomVariables.create([dist1, dist2])
    rvs2 = RandomVariables.create([dist1])
    assert rvs != rvs2
    rvs3 = RandomVariables.create([dist1, dist3])
    assert rvs != rvs3


def test_add():
    dist1 = NormalDistribution.create('ETA(1)', 'iiv', 0, 1)
    dist2 = NormalDistribution.create('ETA(2)', 'iiv', 0, 0.1)
    rvs1 = RandomVariables.create([dist1])
    rvs2 = RandomVariables.create([dist2])
    rvs3 = rvs1 + rvs2
    assert len(rvs3) == 2
    assert len(rvs1 + dist2) == 2
    assert len(dist1 + rvs2) == 2
    with pytest.raises(TypeError):
        rvs1 + None
    with pytest.raises(TypeError):
        None + rvs1


def test_getitem():
    dist1 = NormalDistribution.create('ETA(1)', 'iiv', 0, 1)
    dist2 = NormalDistribution.create('ETA(2)', 'iiv', 0, 0.1)
    rvs = RandomVariables.create([dist1, dist2])
    assert rvs[0] == dist1
    assert rvs[1] == dist2
    assert rvs['ETA(1)'] == dist1
    assert rvs['ETA(2)'] == dist2
    assert rvs[symbol('ETA(1)')] == dist1
    assert rvs[symbol('ETA(2)')] == dist2
    with pytest.raises(IndexError):
        rvs[23]
    with pytest.raises(KeyError):
        rvs['NOKEYOFTHIS']

    dist1 = NormalDistribution.create('ETA(1)', 'iiv', 0, 1)
    dist2 = NormalDistribution.create('ETA(2)', 'iiv', 0, 0.1)
    dist3 = NormalDistribution.create('ETA(3)', 'iiv', 0, 0.1)
    rvs = RandomVariables.create([dist1, dist2, dist3])
    selection = rvs[['ETA(1)', 'ETA(2)']]
    assert len(selection) == 2
    selection = rvs[1:]
    assert len(selection) == 2

    dist1 = JointNormalDistribution.create(
        ['ETA(1)', 'ETA(2)'],
        'iiv',
        [0, 0],
        [
            [symbol('OMEGA(1,1)'), symbol('OMEGA(2,1)')],
            [symbol('OMEGA(2,1)'), symbol('OMEGA(2,2)')],
        ],
    )
    rvs = RandomVariables.create([dist1])
    selection = rvs[['ETA(1)']]
    assert isinstance(selection['ETA(1)'], NormalDistribution)

    with pytest.raises(KeyError):
        rvs[None]


def test_contains():
    dist1 = NormalDistribution.create('ETA(1)', 'iiv', 0, 1)
    dist2 = NormalDistribution.create('ETA(2)', 'iiv', 0, 0.1)
    dist3 = NormalDistribution.create('ETA(3)', 'iiv', 0, 0.1)
    rvs = RandomVariables.create([dist1, dist2, dist3])
    assert 'ETA(2)' in rvs
    assert 'ETA(4)' not in rvs


def test_names():
    dist1 = NormalDistribution.create('ETA1', 'iiv', 0, 1)
    dist2 = NormalDistribution.create('ETA2', 'iiv', 0, 0.1)
    rvs = RandomVariables.create([dist1, dist2])
    assert rvs.names == ['ETA1', 'ETA2']


def test_epsilons():
    dist1 = NormalDistribution.create('ETA', 'iiv', 0, 1)
    dist2 = NormalDistribution.create('ETA2', 'iiv', 0, 0.1)
    dist3 = NormalDistribution.create('EPS', 'ruv', 0, 0.1)
    rvs = RandomVariables.create([dist1, dist2, dist3])
    assert rvs.epsilons == RandomVariables.create([dist3])
    assert rvs.epsilons.names == ['EPS']


def test_etas():
    dist1 = NormalDistribution.create('ETA', 'iiv', 0, 1)
    dist2 = NormalDistribution.create('ETA2', 'iiv', 0, 0.1)
    dist3 = NormalDistribution.create('EPS', 'ruv', 0, 0.1)
    rvs = RandomVariables.create([dist1, dist2, dist3])
    assert rvs.etas == RandomVariables.create([dist1, dist2])
    assert rvs.etas.names == ['ETA', 'ETA2']


def test_iiv_iov():
    dist1 = NormalDistribution.create('ETA', 'iiv', 0, 1)
    dist2 = NormalDistribution.create('ETA2', 'iov', 0, 0.1)
    dist3 = NormalDistribution.create('EPS', 'ruv', 0, 0.1)
    rvs = RandomVariables.create([dist1, dist2, dist3])
    assert rvs.iiv == RandomVariables.create([dist1])
    assert rvs.iiv.names == ['ETA']
    assert rvs.iov == RandomVariables.create([dist2])
    assert rvs.iov.names == ['ETA2']


def test_subs():
    dist1 = JointNormalDistribution.create(
        ['ETA(1)', 'ETA(2)'],
        'iiv',
        [0, 0],
        [
            [symbol('OMEGA(1,1)'), symbol('OMEGA(2,1)')],
            [symbol('OMEGA(2,1)'), symbol('OMEGA(2,2)')],
        ],
    )
    dist2 = NormalDistribution.create('ETA(3)', 'iiv', 0, symbol('OMEGA(3,3)'))
    rvs = RandomVariables.create([dist1, dist2])
    rvs = rvs.subs(
        {
            symbol('ETA(2)'): symbol('w'),
            symbol('OMEGA(1,1)'): symbol('x'),
            symbol('OMEGA(3,3)'): symbol('y'),
        }
    )
    assert rvs['ETA(1)'].variance == sympy.ImmutableMatrix(
        [[symbol('x'), symbol('OMEGA(2,1)')], [symbol('OMEGA(2,1)'), symbol('OMEGA(2,2)')]]
    )
    assert rvs['ETA(3)'].variance == symbol('y')
    assert rvs.names == ['ETA(1)', 'w', 'ETA(3)']


def test_free_symbols():
    dist1 = NormalDistribution.create('ETA(1)', 'iiv', 0, 1)
    dist2 = NormalDistribution.create('ETA(2)', 'iiv', 0, symbol('OMEGA(2,2)'))
    assert dist2.free_symbols == {symbol('ETA(2)'), symbol('OMEGA(2,2)')}
    rvs = RandomVariables.create([dist1, dist2])
    assert rvs.free_symbols == {symbol('ETA(1)'), symbol('ETA(2)'), symbol('OMEGA(2,2)')}


def test_parameter_names():
    dist1 = JointNormalDistribution.create(
        ['ETA(1)', 'ETA(2)'],
        'iiv',
        [0, 0],
        [
            [symbol('OMEGA(1,1)'), symbol('OMEGA(2,1)')],
            [symbol('OMEGA(2,1)'), symbol('OMEGA(2,2)')],
        ],
    )
    assert dist1.parameter_names == ['OMEGA(1,1)', 'OMEGA(2,1)', 'OMEGA(2,2)']
    dist2 = NormalDistribution.create('ETA(3)', 'iiv', 0, symbol('OMEGA(3,3)'))
    assert dist2.parameter_names == ['OMEGA(3,3)']
    rvs = RandomVariables.create([dist1, dist2])
    assert rvs.parameter_names == ['OMEGA(1,1)', 'OMEGA(2,1)', 'OMEGA(2,2)', 'OMEGA(3,3)']


def test_subs_rv():
    dist = NormalDistribution.create('ETA(1)', 'iiv', 0, symbol('OMEGA(3,3)'))
    dist = dist.subs({symbol('OMEGA(3,3)'): symbol('VAR')})
    assert dist.variance == symbol('VAR')


def test_repr():
    dist1 = JointNormalDistribution.create(
        ['ETA(1)', 'ETA(2)'], 'iiv', [0, 0], [[1, 0.1], [0.1, 2]]
    )
    dist2 = NormalDistribution.create('ETA(3)', 'iiv', 2, 1)
    rvs = RandomVariables.create([dist1, dist2])
    res = """⎡ETA(1)⎤    ⎧⎡0⎤  ⎡ 1   0.1⎤⎫
⎢      ⎥ ~ N⎪⎢ ⎥, ⎢        ⎥⎪
⎣ETA(2)⎦    ⎩⎣0⎦  ⎣0.1   2 ⎦⎭
ETA(3) ~ N(2, 1)"""
    assert repr(rvs) == res
    dist3 = JointNormalDistribution.create(
        ['ETA(1)', 'ETA(2)'], 'iiv', [sympy.sqrt(sympy.Rational(2, 5)), 0], [[1, 0.1], [0.1, 2]]
    )
    assert (
        repr(dist3)
        == '''            ⎧⎡√10⎤            ⎫
⎡ETA(1)⎤    ⎪⎢───⎥  ⎡ 1   0.1⎤⎪
⎢      ⎥ ~ N⎪⎢ 5 ⎥, ⎢        ⎥⎪
⎣ETA(2)⎦    ⎪⎢   ⎥  ⎣0.1   2 ⎦⎪
            ⎩⎣ 0 ⎦            ⎭'''
    )


def test_repr_latex():
    dist1 = NormalDistribution.create('z', 'iiv', 0, 1)
    dist2 = JointNormalDistribution.create(['x', 'y'], 'iiv', [0, 0], [[1, 0.1], [0.1, 2]])
    rvs = RandomVariables.create([dist1, dist2])
    assert (
        rvs._repr_latex_()
        == '\\begin{align*}\n\\displaystyle z & \\sim  \\mathcal{N} \\left(\\displaystyle 0,\\displaystyle 1\\right) \\\\ \\displaystyle \\left[\\begin{matrix}x\\\\y\\end{matrix}\\right] & \\sim \\mathcal{N} \\left(\\displaystyle \\left[\\begin{matrix}0\\\\0\\end{matrix}\\right],\\displaystyle \\left[\\begin{matrix}1 & 0.1\\\\0.1 & 2\\end{matrix}\\right]\\right)\\end{align*}'  # noqa E501
    )


def test_pickle():
    dist1 = JointNormalDistribution.create(
        ['ETA(1)', 'ETA(2)'], 'iiv', [0, 0], [[1, 0.1], [0.1, 2]]
    )
    dist2 = NormalDistribution.create('ETA(3)', 'iiv', 2, 1)
    rvs = RandomVariables.create([dist1, dist2])
    pickled = pickle.dumps(rvs)
    obj = pickle.loads(pickled)
    assert obj == rvs


def test_hash():
    dist1 = NormalDistribution.create('ETA(3)', 'iiv', 2, 1)
    dist2 = NormalDistribution.create('ETA(2)', 'iiv', 2, 0)
    assert hash(dist1) != hash(dist2)


def test_nearest_valid_parameters():
    values = {'x': 1, 'y': 0.1, 'z': 2}
    dist1 = JointNormalDistribution.create(
        ['ETA(1)', 'ETA(2)'],
        'iiv',
        [0, 0],
        [[symbol('x'), symbol('y')], [symbol('y'), symbol('z')]],
    )
    rvs = RandomVariables.create([dist1])
    new = rvs.nearest_valid_parameters(values)
    assert values == new
    values = {'x': 1, 'y': 1.1, 'z': 1}
    new = rvs.nearest_valid_parameters(values)
    assert new == {'x': 1.0500000000000005, 'y': 1.0500000000000003, 'z': 1.050000000000001}

    dist2 = NormalDistribution.create('ETA(3)', 'iiv', 2, 1)
    rvs = RandomVariables.create([dist2])
    values = {symbol('ETA(3)'): 5}
    new = rvs.nearest_valid_parameters(values)
    assert new == values


def test_validate_parameters():
    a, b, c, d = (symbol('a'), symbol('b'), symbol('c'), symbol('d'))
    dist1 = JointNormalDistribution.create(
        ['ETA(1)', 'ETA(2)'],
        'iiv',
        [0, 0],
        [[a, b], [c, d]],
    )
    dist2 = NormalDistribution.create('ETA(3)', 'iiv', 0.5, d)
    rvs = RandomVariables.create([dist1, dist2])
    params = {'a': 2, 'b': 0.1, 'c': 1, 'd': 23}
    assert rvs.validate_parameters(params)
    params2 = {'a': 2, 'b': 2, 'c': 23, 'd': 1}
    assert not rvs.validate_parameters(params2)
    with pytest.raises(TypeError):
        rvs.validate_parameters({})


# def test_sample():
#    rv1, rv2 = RandomVariable.joint_normal(
#        ['ETA(1)', 'ETA(2)'],
#        'iiv',
#        [0, 0],
#        [[symbol('a'), symbol('b')], [symbol('b'), symbol('c')]],
#    )
#    rvs = RandomVariables([rv1, rv2])
#    params = {'a': 1, 'b': 0.1, 'c': 2}
#    samples = rvs.sample(rv1.symbol + rv2.symbol, parameters=params, samples=2, rng=9532)
#    assert list(samples) == pytest.approx([1.7033555824617346, -1.4031809274765599])
#    with pytest.raises(TypeError):
#        rvs.sample(rv1.symbol + rv2.symbol, samples=1, rng=9532)
#    samples = rvs.sample(1, samples=2)
#    assert list(samples) == [1.0, 1.0]


def test_variance_parameters():
    dist1 = JointNormalDistribution.create(
        ['ETA(1)', 'ETA(2)'],
        'iiv',
        [0, 0],
        [
            [symbol('OMEGA(1,1)'), symbol('OMEGA(2,1)')],
            [symbol('OMEGA(2,1)'), symbol('OMEGA(2,2)')],
        ],
    )
    dist2 = NormalDistribution.create('ETA(3)', 'iiv', 0, symbol('OMEGA(3,3)'))
    rvs = RandomVariables.create([dist1, dist2])
    assert rvs.variance_parameters == ['OMEGA(1,1)', 'OMEGA(2,2)', 'OMEGA(3,3)']

    dist1 = NormalDistribution.create('x', 'iiv', 0, symbol('omega'))
    dist2 = NormalDistribution.create('y', 'iiv', 0, symbol('omega'))
    rvs = RandomVariables.create([dist1, dist2])
    assert rvs.variance_parameters == ['omega']

    dist3 = JointNormalDistribution.create(
        ['ETA(1)', 'ETA(2)'],
        'iiv',
        [0, 0],
        [
            [symbol('OMEGA(1,1)'), symbol('OMEGA(2,1)')],
            [symbol('OMEGA(2,1)'), symbol('OMEGA(1,1)')],
        ],
    )
    rvs = RandomVariables.create([dist3])
    assert rvs.variance_parameters == ['OMEGA(1,1)']


def test_get_variance():
    dist1 = JointNormalDistribution.create(
        ['ETA(1)', 'ETA(2)'],
        'iiv',
        [0, 0],
        [
            [symbol('OMEGA(1,1)'), symbol('OMEGA(2,1)')],
            [symbol('OMEGA(2,1)'), symbol('OMEGA(2,2)')],
        ],
    )
    dist2 = NormalDistribution.create('ETA(3)', 'iiv', 0, symbol('OMEGA(3,3)'))
    rvs = RandomVariables.create([dist1, dist2])
    assert rvs['ETA(1)'].get_variance('ETA(1)') == symbol('OMEGA(1,1)')
    assert rvs['ETA(3)'].get_variance('ETA(3)') == symbol('OMEGA(3,3)')


def test_get_covariance():
    dist1 = JointNormalDistribution.create(
        ['ETA(1)', 'ETA(2)'],
        'iiv',
        [0, 0],
        [
            [symbol('OMEGA(1,1)'), symbol('OMEGA(2,1)')],
            [symbol('OMEGA(2,1)'), symbol('OMEGA(2,2)')],
        ],
    )
    dist2 = NormalDistribution.create('ETA(3)', 'iiv', 0, symbol('OMEGA(3,3)'))
    rvs = RandomVariables.create([dist1, dist2])
    assert rvs.get_covariance('ETA(1)', 'ETA(2)') == symbol('OMEGA(2,1)')
    assert rvs.get_covariance('ETA(3)', 'ETA(2)') == 0


def test_unjoin():
    dist1 = JointNormalDistribution.create(
        ['eta1', 'eta2', 'eta3'], 'iiv', [1, 2, 3], [[9, 2, 3], [4, 8, 6], [1, 2, 9]]
    )
    rvs = RandomVariables.create([dist1])
    new = rvs.unjoin('eta1')
    assert new.nrvs == 3
    assert isinstance(new['eta1'], NormalDistribution)
    assert isinstance(new['eta2'], JointNormalDistribution)


def test_join():
    dist1 = NormalDistribution.create('ETA(1)', 'iiv', 0, symbol('OMEGA(1,1)'))
    dist2 = NormalDistribution.create('ETA(2)', 'iiv', 0, symbol('OMEGA(2,2)'))
    dist3 = NormalDistribution.create('ETA(3)', 'iiv', 0, symbol('OMEGA(3,3)'))
    dist4 = JointNormalDistribution.create(
        ['ETA(4)', 'ETA(5)'],
        'iiv',
        [0, 0],
        [
            [symbol('OMEGA(4,4)'), symbol('OMEGA(5,4)')],
            [symbol('OMEGA(5,4)'), symbol('OMEGA(5,5)')],
        ],
    )
    dist5 = NormalDistribution.create('EPS(1)', 'ruv', 0, symbol('SIGMA(1,1)'))

    rvs = RandomVariables.create([dist1, dist2])
    joined_rvs, _ = rvs.join(['ETA(1)', 'ETA(2)'])
    assert len(joined_rvs) == 1
    assert joined_rvs[0].variance == sympy.Matrix(
        [[symbol('OMEGA(1,1)'), 0], [0, symbol('OMEGA(2,2)')]]
    )

    joined_rvs, _ = rvs.join(['ETA(1)', 'ETA(2)'], fill=1)
    assert joined_rvs[0].variance == sympy.Matrix(
        [[symbol('OMEGA(1,1)'), 1], [1, symbol('OMEGA(2,2)')]]
    )

    joined_rvs, _ = rvs.join(
        ['ETA(1)', 'ETA(2)'], name_template='IIV_{}_IIV_{}', param_names=['CL', 'V']
    )
    assert joined_rvs[0].variance == sympy.Matrix(
        [
            [symbol('OMEGA(1,1)'), symbol('IIV_CL_IIV_V')],
            [symbol('IIV_CL_IIV_V'), symbol('OMEGA(2,2)')],
        ]
    )

    rvs3 = RandomVariables.create([dist1, dist2, dist3])
    joined_rvs, _ = rvs3.join(['ETA(2)', 'ETA(3)'])
    assert joined_rvs[1].variance == sympy.Matrix(
        [[symbol('OMEGA(2,2)'), 0], [0, symbol('OMEGA(3,3)')]]
    )

    rvs5 = RandomVariables.create([dist1, dist2, dist3, dist4, dist5])
    with pytest.raises(KeyError):
        rvs5.join(['ETA(1)', 'ETA(23)'])


def test_parameters_sdcorr():
    dist1 = NormalDistribution.create('ETA(1)', 'iiv', 0, symbol('OMEGA(1,1)'))
    dist2 = NormalDistribution.create('ETA(2)', 'iiv', 0, symbol('OMEGA(2,2)'))
    rvs = RandomVariables.create([dist1, dist2])
    params = rvs.parameters_sdcorr({'OMEGA(1,1)': 4})
    assert params == {'OMEGA(1,1)': 2}
    params = rvs.parameters_sdcorr({'OMEGA(1,1)': 4, 'OMEGA(2,2)': 16})
    assert params == {'OMEGA(1,1)': 2, 'OMEGA(2,2)': 4}

    dist2 = JointNormalDistribution.create(
        ['ETA(1)', 'ETA(2)'],
        'iiv',
        [0, 0],
        [[symbol('x'), symbol('y')], [symbol('y'), symbol('z')]],
    )
    rvs = RandomVariables.create([dist2])
    params = rvs.parameters_sdcorr({'x': 4, 'y': 0.5, 'z': 16, 'k': 23})
    assert params == {'x': 2.0, 'y': 0.0625, 'z': 4.0, 'k': 23}


def test_variability_hierarchy():
    lev1 = VariabilityLevel('IIV', reference=True, group='ID')
    levs = VariabilityHierarchy([lev1])
    assert levs[0].name == 'IIV'
    with pytest.raises(IndexError):
        levs[1].name
    lev2 = VariabilityLevel('CENTER', reference=False, group='CENTER')
    levs2 = VariabilityHierarchy([lev2, lev1])
    assert len(levs2) == 2
    lev3 = VariabilityLevel('PLANET', reference=False, group='PLANET')
    levs3 = VariabilityHierarchy([lev3, lev2, lev1])
    assert len(levs3) == 3

    levs4 = levs + lev2
    assert len(levs4) == 2
    levs5 = lev2 + levs
    assert len(levs5) == 2


def test_covariance_matrix():
    dist1 = NormalDistribution.create('ETA(1)', 'iiv', 0, symbol('OMEGA(1,1)'))
    dist2 = NormalDistribution.create('ETA(2)', 'iiv', 0, symbol('OMEGA(2,2)'))
    rvs = RandomVariables.create([dist1, dist2])
    assert len(rvs.covariance_matrix) == 4

    dist3 = JointNormalDistribution.create(
        ['ETA(3)', 'ETA(4)'],
        'iiv',
        [0, 0],
        [[symbol('x'), symbol('y')], [symbol('y'), symbol('z')]],
    )
    rvs = RandomVariables.create([dist1, dist2, dist3])
    cov = rvs.covariance_matrix
    assert cov == sympy.Matrix(
        [
            [symbol('OMEGA(1,1)'), 0, 0, 0],
            [0, symbol('OMEGA(2,2)'), 0, 0],
            [0, 0, symbol('x'), symbol('y')],
            [0, 0, symbol('y'), symbol('z')],
        ]
    )

    rvs = RandomVariables.create([dist1, dist3, dist2])
    cov = rvs.covariance_matrix
    assert cov == sympy.Matrix(
        [
            [symbol('OMEGA(1,1)'), 0, 0, 0],
            [0, symbol('x'), symbol('y'), 0],
            [0, symbol('y'), symbol('z'), 0],
            [0, 0, 0, symbol('OMEGA(2,2)')],
        ]
    )
