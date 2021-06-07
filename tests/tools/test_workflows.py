import pytest

from pharmpy.tools.workflows import Task, Workflow


@pytest.fixture
def tasks():
    t1 = Task('t1', 'func', 'input')
    t2 = Task('t2', 'func', t1)
    t3 = Task('t3', 'func', t1)
    t4 = Task('t4', 'func', [t2, t3])
    return t1, t2, t3, t4


def test_create_tasks():
    t1 = Task('t1', 'func', 'input')
    assert t1.task_input[0] == 'input'
    t2 = Task('t2', 'func', 1)
    assert t2.task_input[0] == 1
    t3 = Task('t3', 'func', 1, 2, 3)
    assert t3.task_input[2] == 3
    t4 = Task('t4', 'func', [1, 2, 3])
    assert t4.task_input[0] == [1, 2, 3]


def test_add_tasks(tasks):
    wf = Workflow()

    t1, t2, t3, _ = tasks

    wf.add_tasks(t1)
    assert len(list(wf.tasks.nodes)) == 1

    wf.add_tasks([t2, t3])
    assert len(list(wf.tasks.nodes)) == 3


def test_connect_tasks(tasks):
    wf = Workflow()

    t1, t2, t3, t4 = tasks

    wf.add_tasks([t1, t2, t3, t4])
    wf.connect_tasks({t1: [t2, t3], t2: t4, t3: t4})

    assert list(wf.tasks.successors(t1)) == [t2, t3]
    assert list(wf.tasks.predecessors(t4)) == [t2, t3]

    with pytest.raises(ValueError):
        wf.connect_tasks({t1: t1})


def test_get_leaf_tasks(tasks):
    wf = Workflow()

    t1, t2, t3, t4 = tasks

    wf.add_tasks([t1, t2, t3])
    wf.connect_tasks({t1: [t2, t3]})

    assert wf.get_leaf_tasks() == [t2, t3]

    wf.add_tasks(t4)
    wf.connect_tasks({t2: t4, t3: t4})

    assert wf.get_leaf_tasks() == [t4]


def test_as_dict(tasks):
    wf = Workflow()

    t1, t2, t3, t4 = tasks

    wf.add_tasks([t1, t2, t3, t4])
    wf.connect_tasks({t1: [t2, t3], t2: t4, t3: t4})

    wf_dict = wf.as_dict()
    wf_keys = list(wf_dict.keys())
    wf_inputs = [task_input for (_, task_input) in wf_dict.values()]

    assert wf_keys[0].startswith('t1') and wf_keys[1].startswith('t2')
    assert wf_inputs[0].startswith('input')
    assert wf_inputs[1].startswith('t1')
    assert isinstance(wf_inputs[3], list)


def test_merge_workflows(tasks):
    t1, t2, t3, _ = tasks

    wf_sequential = Workflow([t1, t2, t3])
    wf_sequential.connect_tasks({t1: [t2, t3]})
    assert len(wf_sequential.tasks.edges) == 2
    assert list(wf_sequential.tasks.successors(t1)) == [t2, t3]

    t4 = Task('t4', 'func', 'input')
    wf_t4 = Workflow(t4)

    wf_sequential.merge_workflows(wf_t4, connect=True)
    assert list(wf_sequential.tasks.predecessors(t4)) == [t2, t3]
    assert len(wf_sequential.tasks.edges) == 4
    assert list(wf_sequential.tasks.nodes) == [t1, t2, t3, t4]

    wf_parallel = Workflow([t1, t2, t3])
    wf_parallel.connect_tasks({t1: [t2, t3]})
    wf_parallel.merge_workflows(wf_t4, connect=False)
    assert not list(wf_parallel.tasks.predecessors(t4))
    assert len(wf_parallel.tasks.edges) == 2
    assert list(wf_parallel.tasks.nodes) == [t1, t2, t3, t4]
