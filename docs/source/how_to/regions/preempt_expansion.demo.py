from pyfcstm.model import load_state_machine_from_file

print(load_state_machine_from_file("preempt_group.fcstm").to_ast_node())
