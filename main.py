from robotengine import Engine, InputDevice
from robotengine import Node
from robot import Robot


if __name__ == '__main__':
    root = Node("Root")
    
    robot = Robot(warn=False)
    root.add_child(robot)

    root.print_tree()

    engine = Engine(root, frequency=180, input_devices=[])
    engine.run()


