import sys
import os
from pyfcstm.convert.sysdesim.parser import SysDesimParser
from pyfcstm.convert.sysdesim.ast import convert_state_machine_to_ast_node
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.model import parse_dsl_node_to_state_machine

def audit_model_topology(node, model_index):
    """
    对生成的 AST 进行拓扑审计，检查是否存在逻辑断裂。
    鲁棒性体现：通过分析状态迁移关系，自动发现孤立节点。
    """
    states = [s.name for s in node.substates if s.name != '[*]']
    # 收集所有出现在 transition 中的起点和终点
    sources = {t.from_state for t in node.transitions if t.from_state}
    targets = {t.to_state for t in node.transitions if t.to_state}
    
    print(f"\n--- 模型 [{model_index}] 拓扑审计报告 ---")
    print(f"  状态总数: {len(states)} | 连线总数: {len(node.transitions)}")
    
    isolated_states = []
    for s in states:
        if s not in sources and s not in targets:
            isolated_states.append(s)
    
    if not isolated_states:
        print("  ✅ 拓扑检查通过: 未发现孤立状态节点（所有状态均有连线接入或引出）。")
    else:
        print(f"  ⚠️ 拓扑告警: 发现孤立节点 {isolated_states}。请核实 XML 中是否定义了对应的跳转。")

def verify(file_path):
    if not os.path.exists(file_path):
        print(f"❌ 错误: 找不到输入文件 {file_path}")
        return

    print(f"=== 开始全量鲁棒性验证: {file_path} ===")
    
    try:
        # 1. 加载 XML
        s = SysDesimParser.parse_file(file_path)
        model = s.parse_model(s.get_model_elements()[0])
        print("✅ Step 1: XML 数据解析完成")

        # 2. 执行转换 (调用 SysMLConverter 类逻辑)
        nodes = convert_state_machine_to_ast_node(model.clazz.state_machine, model)
        print(f"✅ Step 2: 转换完成，识别到 {len(nodes)} 个并发区域并进行了拆分")

        # 3. 逐个模型审计
        for i, node in enumerate(nodes):
            # 执行闭环解析验证
            dsl_code = str(node)
            try:
                ast_node = parse_with_grammar_entry(dsl_code, entry_name='state_machine_dsl')
                parse_dsl_node_to_state_machine(ast_node)
                print(f"\n✅ 模型 [{i}] 闭环解析验证成功 (语法 100% 合法)")
            except Exception as e:
                print(f"\n❌ 模型 [{i}] 闭环解析失败: {e}")
                continue

            # 执行拓扑审计 (检测师兄关心的断裂问题)
            audit_model_topology(node, i)
            
            # 生成 Puml 文件供视觉比对
            puml_name = f"final_output_{i}.puml"
            with open(puml_name, "w", encoding="utf-8") as f:
                # 重新读回 model 以调用 to_plantuml
                re_model = parse_dsl_node_to_state_machine(ast_node)
                f.write(re_model.to_plantuml())
            print(f"  👉 已生成可视化文件: {puml_name}")

    except Exception as e:
        print(f"💥 验证过程发生意外中断: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 鲁棒性设计：支持命令行传参或默认文件
    input_file = sys.argv[1] if len(sys.argv) > 1 else 'input_model.xml'
    verify(input_file)