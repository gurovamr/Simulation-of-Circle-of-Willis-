import vtk
import os

# TODO: Change path 
#graph_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'media/output_final/cow_graphs')
graph_dir = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "..", "CoW_Centerline_Data", "cow_graphs")
)


filename = 'topcow_mr_025.vtp'

print(f"Reading graph from file: {filename}")
reader = vtk.vtkXMLPolyDataReader()
reader.SetFileName(os.path.join(graph_dir, filename))
reader.Update()
graph = reader.GetOutput()

print(f"\nNumber of points in the graph: {graph.GetNumberOfPoints()}")

# get some specific point
point_id = 10
point = graph.GetPoint(point_id)
print(f"Coordinates of point {point_id}: {point}")

# get some specific cell
cell_id = 10
cell = graph.GetCell(cell_id)
print(f"\nNumber of points in cell {cell_id}: {cell.GetNumberOfPoints()}")
print(f"Point IDs in cell {cell_id}: {[cell.GetPointId(i) for i in range(cell.GetNumberOfPoints())]}")

# extract cell attribute
ce_radius_array = graph.GetCellData().GetArray('ce_radius')
if ce_radius_array:
    radius_value = ce_radius_array.GetValue(cell_id)
    print(f"\nRadius at cell {cell_id}: {radius_value}")

# extract point attribute
point_degree = graph.GetPointData().GetArray('degree')
if point_degree:
    degree_value = point_degree.GetValue(point_id)
    print(f"Degree at point {point_id}: {degree_value}")
