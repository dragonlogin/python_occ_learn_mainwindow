# 导入必要的库
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire  # 用于创建边、面和线框
from OCC.Core.gp import gp_Pnt, gp_Vec  # 用于创建点和向量
from OCC.Display.SimpleGui import init_display  # 用于初始化显示
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB  # 用于设置颜色
import numpy as np  # 用于向量运算

# 定义结构体LineWithNormals，包含线段的两个端点和两个面的法向
class LineWithNormals:
    def __init__(self, start, end, normal1, normal2):
        """初始化线段对象
        
        Args:
            start: 线段的起点坐标 [x, y, z]
            end: 线段的终点坐标 [x, y, z]
            normal1: 第一个面的法向量 [nx, ny, nz]
            normal2: 第二个面的法向量 [nx, ny, nz]
        """
        self.start = np.array(start)  # 将起点坐标转换为numpy数组
        self.end = np.array(end)  # 将终点坐标转换为numpy数组
        self.normal1 = np.array(normal1)  # 将第一个法向量转换为numpy数组
        self.normal2 = np.array(normal2)  # 将第二个法向量转换为numpy数组
    
    def direction(self):
        """计算线段的方向向量
        
        Returns:
            numpy数组: 线段的方向向量
        """
        return self.end - self.start  # 终点减去起点得到方向向量
    
    def length(self):
        """计算线段的长度
        
        Returns:
            float: 线段的长度
        """
        return np.linalg.norm(self.direction())  # 计算方向向量的模长，即线段长度

def create_face(vertices):
    """从四个顶点创建面
    
    Args:
        vertices: 包含四个顶点坐标的列表，每个顶点为 [x, y, z]
    
    Returns:
        TopoDS_Face: 创建的面对象，如果创建失败则返回None
    """
    # 检查顶点数量
    if len(vertices) != 4:
        return None  # 如果顶点数量不是4，返回None
    
    # 创建线框
    wire = BRepBuilderAPI_MakeWire()  # 初始化线框构建器
    
    # 添加边到线框
    edge_count = 0  # 记录创建的边数量
    for i in range(4):
        # 确保使用浮点数
        x1, y1, z1 = float(vertices[i][0]), float(vertices[i][1]), float(vertices[i][2])
        x2, y2, z2 = float(vertices[(i+1)%4][0]), float(vertices[(i+1)%4][1]), float(vertices[(i+1)%4][2])
        
        # 检查点是否重合
        if abs(x1 - x2) < 1e-6 and abs(y1 - y2) < 1e-6 and abs(z1 - z2) < 1e-6:
            continue  # 如果两个点重合，跳过创建边
        
        try:
            p1 = gp_Pnt(x1, y1, z1)  # 创建第一个点
            p2 = gp_Pnt(x2, y2, z2)  # 创建第二个点
            edge_builder = BRepBuilderAPI_MakeEdge(p1, p2)  # 创建边构建器
            if edge_builder.IsDone():
                edge = edge_builder.Edge()  # 获取创建的边
                wire.Add(edge)  # 将边添加到线框
                edge_count += 1  # 边数量加1
        except Exception as e:
            print(f"Error creating edge: {e}")  # 打印错误信息
            continue  # 继续处理下一条边
    
    # 检查是否创建了足够的边
    if edge_count < 3:
        print(f"Not enough edges to create face, only {edge_count} edges created")
        return None  # 如果边数量少于3，无法创建面，返回None
    
    # 创建面
    try:
        if wire.IsDone():
            face_builder = BRepBuilderAPI_MakeFace(wire.Wire())  # 创建面构建器
            if face_builder.IsDone():
                face = face_builder.Face()  # 获取创建的面
                return face  # 返回创建的面
            else:
                print("Failed to create face: wire is not valid")
                return None  # 如果线框无效，返回None
        else:
            print("Failed to create wire")
            return None  # 如果线框创建失败，返回None
    except Exception as e:
        print(f"Error creating face: {e}")  # 打印错误信息
        return None  # 如果创建面失败，返回None

def create_normal_vector(start_point, normal, length=2.0):
    """创建法向量作为边
    
    Args:
        start_point: 法向量的起点坐标 [x, y, z]
        normal: 法向量的方向 [nx, ny, nz]
        length: 法向量的长度，默认为2.0
    
    Returns:
        TopoDS_Edge: 表示法向量的边对象
    """
    # 计算终点
    end_point = start_point + np.array(normal) * length  # 起点加上法向量方向的长度
    
    # 创建边
    edge = BRepBuilderAPI_MakeEdge(
        gp_Pnt(start_point[0], start_point[1], start_point[2]),  # 法向量起点
        gp_Pnt(end_point[0], end_point[1], end_point[2])  # 法向量终点
    ).Edge()  # 创建边并获取结果
    
    return edge  # 返回创建的边

def calculate_face_center(vertices):
    """计算面的中心点
    
    Args:
        vertices: 包含面顶点坐标的列表，每个顶点为 [x, y, z]
    
    Returns:
        numpy数组: 面的中心点坐标 [x, y, z]
    """
    center = np.zeros(3)  # 初始化中心点为原点
    for vertex in vertices:
        center += vertex  # 累加所有顶点坐标
    return center / len(vertices)  # 除以顶点数量得到平均值，即中心点

def draw_coordinate_system(display, size):
    """绘制坐标系
    
    Args:
        display: 显示对象
        size: 坐标系轴的长度
    """
    # X轴（红色）
    x_axis = BRepBuilderAPI_MakeEdge(
        gp_Pnt(0, 0, 0),  # 原点
        gp_Pnt(size, 0, 0)  # X轴终点
    ).Edge()  # 创建X轴边
    display.DisplayShape(x_axis, color=Quantity_Color(1, 0, 0, Quantity_TOC_RGB), update=False)  # 显示X轴，红色
    
    # Y轴（绿色）
    y_axis = BRepBuilderAPI_MakeEdge(
        gp_Pnt(0, 0, 0),  # 原点
        gp_Pnt(0, size, 0)  # Y轴终点
    ).Edge()  # 创建Y轴边
    display.DisplayShape(y_axis, color=Quantity_Color(0, 1, 0, Quantity_TOC_RGB), update=False)  # 显示Y轴，绿色
    
    # Z轴（蓝色）
    z_axis = BRepBuilderAPI_MakeEdge(
        gp_Pnt(0, 0, 0),  # 原点
        gp_Pnt(0, 0, size)  # Z轴终点
    ).Edge()  # 创建Z轴边
    display.DisplayShape(z_axis, color=Quantity_Color(0, 0, 1, Quantity_TOC_RGB), update=False)  # 显示Z轴，蓝色
    
    # 添加轴标签
    display.DisplayMessage(gp_Pnt(size * 1.1, 0, 0), "X", update=False)  # 显示X轴标签
    display.DisplayMessage(gp_Pnt(0, size * 1.1, 0), "Y", update=False)  # 显示Y轴标签
    display.DisplayMessage(gp_Pnt(0, 0, size * 1.1), "Z", update=False)  # 显示Z轴标签

def find_common_normal(lines):
    """找到多条线段的公共法向量
    
    Args:
        lines: 线段对象列表
    
    Returns:
        list: 公共法向量 [nx, ny, nz]，如果没有找到则返回None
    """
    if len(lines) < 2:
        return None  # 如果线段数量少于2，无法找到公共法向量
    
    # 收集所有法向量
    all_normals = []
    for line in lines:
        all_normals.append(line.normal1)  # 添加第一条法向量
        all_normals.append(line.normal2)  # 添加第二条法向量
    
    # 检查哪些法向量是公共的
    normal_counts = {}  # 用于统计法向量出现的次数
    for normal in all_normals:
        key = tuple(normal)  # 将法向量转换为元组作为字典键
        if key in normal_counts:
            normal_counts[key] += 1  # 法向量出现次数加1
        else:
            normal_counts[key] = 1  # 初始化法向量出现次数为1
    
    # 找到出现次数等于线段数量的法向量（公共法向量）
    for normal, count in normal_counts.items():
        if count >= len(lines):  # 如果法向量出现次数大于等于线段数量
            return list(normal)  # 返回该法向量
    
    return None  # 如果没有找到公共法向量，返回None

def calculate_far_corner(line1, line2, common_normal):
    """计算两条线段形成的面的远角点
    
    Args:
        line1: 第一条线段对象
        line2: 第二条线段对象
        common_normal: 两条线段的公共法向量
    
    Returns:
        numpy数组: 远角点坐标 [x, y, z]
    """
    # 计算两条线段的方向向量
    dir1 = line1.direction()  # 第一条线段的方向向量
    dir2 = line2.direction()  # 第二条线段的方向向量
    
    # 远角点 = 第一条线段的终点 + 第二条线段的方向向量
    far_corner = line1.end + dir2
    
    # 验证远角点是否正确
    # 检查远角点是否在两条线段所形成的平面上
    # 平面方程：(P - P0) · normal = 0
    p0 = line1.start  # 平面上的一点（线段1的起点）
    if abs(np.dot(far_corner - p0, common_normal)) > 1e-6:  # 如果点不在平面上
        # 如果不在平面上，尝试另一种计算方法
        far_corner = line2.end + dir1  # 远角点 = 第二条线段的终点 + 第一条线段的方向向量
    
    return far_corner  # 返回远角点

def calculate_face_vertices_from_lines(line1, line2, common_normal):
    """根据两条线段计算面的顶点
    
    Args:
        line1: 第一条线段对象
        line2: 第二条线段对象
        common_normal: 两条线段的公共法向量
    
    Returns:
        list: 面的四个顶点坐标，每个顶点为 [x, y, z]，如果顶点无效则返回空列表
    """
    # 计算远角点
    far_corner = calculate_far_corner(line1, line2, common_normal)  # 计算远角点
    
    # 构建面的顶点
    face_vertices = [
        line1.start.tolist(),  # 原点（线段1的起点）
        line1.end.tolist(),    # 第一条线段的终点
        far_corner.tolist(),   # 远角点
        line2.end.tolist()     # 第二条线段的终点
    ]
    
    # 过滤掉包含无效顶点的面（比如(0,10,0)这样的点）
    # 检查所有顶点是否都在合理范围内
    max_coord = 5.0  # 最大坐标值
    for vertex in face_vertices:
        for coord in vertex:
            if abs(coord) > max_coord * 1.1:  # 允许10%的误差
                return []  # 如果顶点坐标超出范围，返回空列表
    
    return face_vertices  # 返回面的顶点

def process_three_lines(lines):
    """处理三条正交线段，计算三个面的顶点
    
    Args:
        lines: 包含三条线段的列表
    
    Returns:
        tuple: 包含三个面的顶点和法向量的元组
    """
    if len(lines) != 3:
        return []  # 如果线段数量不是3，返回空列表
    
    # 计算三个面的顶点
    # 面1：线段1和线段2形成的面
    normal1 = find_common_normal([lines[0], lines[1]])  # 找到线段1和线段2的公共法向量
    face1_vertices = calculate_face_vertices_from_lines(lines[0], lines[1], normal1)  # 计算面1的顶点
    
    # 面2：线段2和线段3形成的面
    normal2 = find_common_normal([lines[1], lines[2]])  # 找到线段2和线段3的公共法向量
    face2_vertices = calculate_face_vertices_from_lines(lines[1], lines[2], normal2)  # 计算面2的顶点
    
    # 面3：线段3和线段1形成的面
    normal3 = find_common_normal([lines[2], lines[0]])  # 找到线段3和线段1的公共法向量
    face3_vertices = calculate_face_vertices_from_lines(lines[2], lines[0], normal3)  # 计算面3的顶点
    
    return face1_vertices, face2_vertices, face3_vertices, normal1, normal2, normal3  # 返回三个面的顶点和法向量

def process_multiple_lines(lines):
    """处理多条线段，计算所有可能的面
    
    Args:
        lines: 线段对象列表
    
    Returns:
        list: 包含面信息的列表，每个面信息包含面对象、顶点、中心点、法向量等
    """
    if len(lines) < 2:
        return []  # 如果线段数量少于2，返回空列表
    
    # 存储所有面的信息
    faces = []  # 用于存储所有有效的面
    
    # 遍历所有线段对，计算可能的面
    for i in range(len(lines)):
        for j in range(i+1, len(lines)):
            line1 = lines[i]  # 第一条线段
            line2 = lines[j]  # 第二条线段
            
            # 找到公共法向量
            common_normal = find_common_normal([line1, line2])  # 找到两条线段的公共法向量
            if common_normal:  # 如果找到公共法向量
                # 计算面的顶点
                face_vertices = calculate_face_vertices_from_lines(line1, line2, common_normal)  # 计算面的顶点
                if face_vertices:  # 如果顶点有效
                    # 检查是否已经存在相同的面
                    face_exists = False
                    for existing_face in faces:
                        existing_vertices = existing_face['vertices']
                        # 检查顶点是否相同（顺序可能不同）
                        if set(tuple(v) for v in face_vertices) == set(tuple(v) for v in existing_vertices):
                            face_exists = True
                            break
                    
                    if not face_exists:  # 如果面不存在
                        # 创建面
                        face = create_face(face_vertices)  # 创建面
                        if face is not None:  # 如果面创建成功
                            # 检查面是否为正方形
                            # 计算所有边的长度
                            edge_lengths = []
                            for k in range(4):
                                v1 = np.array(face_vertices[k])
                                v2 = np.array(face_vertices[(k+1)%4])
                                length = np.linalg.norm(v1 - v2)  # 计算边的长度
                                edge_lengths.append(length)
                            
                            # 检查所有边的长度是否相近（正方形）
                            max_length = max(edge_lengths)
                            min_length = min(edge_lengths)
                            if max_length / min_length < 1.1:  # 允许10%的误差
                                # 计算面中心点
                                face_center = calculate_face_center(face_vertices)  # 计算面的中心点
                                # 创建法向量
                                normal_vector = create_normal_vector(face_center, common_normal)  # 创建法向量
                                
                                # 添加到面列表
                                faces.append({
                                    'face': face,  # 面对象
                                    'vertices': face_vertices,  # 面的顶点
                                    'center': face_center,  # 面的中心点
                                    'normal': common_normal,  # 面的法向量
                                    'normal_vector': normal_vector  # 表示法向量的边
                                })
                            else:
                                print(f"Skipping non-square face with edge lengths: {edge_lengths}")  # 跳过非正方形的面
                        else:
                            print(f"Skipping invalid face with vertices: {face_vertices}")  # 跳过无效的面
    
    return faces

def main(input_lines=None):
    """主函数
    
    Args:
        input_lines: 线段对象列表，如果为None则使用默认线段
    """
    # 如果没有输入，使用默认的五条线段
    if input_lines is None:
        # 线段A: 起点(0,0,0)，终点(0,5,0)，法向[(0,0,1),(1,0,0)]
        lineA = LineWithNormals(
            start=[0, 0, 0],  # 起点坐标
            end=[0, 5, 0],  # 终点坐标
            normal1=[0, 0, 1],  # 第一个法向量
            normal2=[1, 0, 0]  # 第二个法向量
        )
        
        # 线段B: 起点(0,0,0)，终点(5,0,0)，法向[(0,0,1),(0,1,0)]
        lineB = LineWithNormals(
            start=[0, 0, 0],  # 起点坐标
            end=[5, 0, 0],  # 终点坐标
            normal1=[0, 0, 1],  # 第一个法向量
            normal2=[0, 1, 0]  # 第二个法向量
        )
        
        # 线段C: 起点(0,0,0)，终点(0,0,5)，法向[(1,0,0),(0,1,0)]
        lineC = LineWithNormals(
            start=[0, 0, 0],  # 起点坐标
            end=[0, 0, 5],  # 终点坐标
            normal1=[1, 0, 0],  # 第一个法向量
            normal2=[0, 1, 0]  # 第二个法向量
        )
        
        # 线段D: 起点(5,0,0)，终点(5,0,5)，法向[(-1,0,0),(0,1,0)]
        lineD = LineWithNormals(
            start=[5, 0, 0],  # 起点坐标
            end=[5, 0, 5],  # 终点坐标
            normal1=[-1, 0, 0],  # 第一个法向量
            normal2=[0, 1, 0]  # 第二个法向量
        )
        
        # 线段E: 起点(5,0,0)，终点(5,5,0)，法向[(-1,0,0),(0,0,1)]
        lineE = LineWithNormals(
            start=[5, 0, 0],  # 起点坐标
            end=[5, 5, 0],  # 终点坐标
            normal1=[-1, 0, 0],  # 第一个法向量
            normal2=[0, 0, 1]  # 第二个法向量
        )
        
        input_lines = [lineA, lineB, lineC, lineD, lineE]  # 构建输入线段列表
    
    # 处理多条线段
    faces = process_multiple_lines(input_lines)  # 处理输入的线段，计算所有可能的面
    
    # 初始化显示
    display, start_display, _, _ = init_display()  # 初始化显示对象
    
    # 收集所有顶点，用于计算坐标系大小
    all_vertices = []
    for face_info in faces:
        all_vertices.extend(face_info['vertices'])  # 收集所有面的顶点
    
    # 计算坐标系大小
    if all_vertices:
        max_coord = max(max(abs(coord) for coord in vertex) for vertex in all_vertices)  # 找到最大坐标值
        coord_system_size = max_coord * 1.5  # 坐标系大小为最大坐标值的1.5倍
        
        # 绘制坐标系
        draw_coordinate_system(display, coord_system_size)  # 绘制坐标系
    else:
        coord_system_size = 10.0  # 默认坐标系大小
        draw_coordinate_system(display, coord_system_size)  # 绘制坐标系
    
    # 显示所有面和法向量
    colors = [
        (1, 0, 0),  # 红色
        (0, 1, 0),  # 绿色
        (0, 0, 1),  # 蓝色
        (1, 1, 0),  # 黄色
        (1, 0, 1),  # 洋红色
        (0, 1, 1),  # 青色
        (0.5, 0.5, 0.5)  # 灰色
    ]  # 面的颜色列表
    
    for i, face_info in enumerate(faces):
        color = colors[i % len(colors)]  # 循环使用颜色列表
        # 显示面
        display.DisplayShape(face_info['face'], 
                           color=Quantity_Color(color[0], color[1], color[2], Quantity_TOC_RGB), 
                           update=False)  # 显示面，使用指定颜色
        # 显示法向量
        display.DisplayShape(face_info['normal_vector'], 
                           color=Quantity_Color(color[0], color[1], color[2], Quantity_TOC_RGB), 
                           update=False)  # 显示法向量，使用与面相同的颜色
    
    # 显示输入线段
    for line in input_lines:
        line_edge = BRepBuilderAPI_MakeEdge(
            gp_Pnt(float(line.start[0]), float(line.start[1]), float(line.start[2])),  # 线段起点
            gp_Pnt(float(line.end[0]), float(line.end[1]), float(line.end[2]))  # 线段终点
        ).Edge()  # 创建线段边
        display.DisplayShape(line_edge, color=Quantity_Color(1, 1, 1, Quantity_TOC_RGB), update=False)  # 显示线段，白色
    
    # 显示坐标值
    for i, face_info in enumerate(faces):
        # 显示面中心点坐标
        center = face_info['center']  # 面的中心点
        display.DisplayMessage(gp_Pnt(float(center[0]), float(center[1]), float(center[2])), 
                              f"({center[0]:.1f}, {center[1]:.1f}, {center[2]:.1f})", 
                              update=False)  # 显示中心点坐标
        
        # 显示法向量终点坐标
        normal_end = center + np.array(face_info['normal']) * 2.0  # 法向量终点
        display.DisplayMessage(gp_Pnt(float(normal_end[0]), float(normal_end[1]), float(normal_end[2])), 
                              f"({normal_end[0]:.1f}, {normal_end[1]:.1f}, {normal_end[2]:.1f})", 
                              update=False)  # 显示法向量终点坐标
    
    # 显示顶点坐标
    for vertex in all_vertices:
        display.DisplayMessage(gp_Pnt(float(vertex[0]), float(vertex[1]), float(vertex[2])), 
                              f"({vertex[0]}, {vertex[1]}, {vertex[2]})", 
                              update=False)  # 显示顶点坐标
    
    # 调整视图
    display.FitAll()  # 调整视图以显示所有内容
    start_display()  # 开始显示

  # 调用主函数

if __name__ == "__main__":
    main()