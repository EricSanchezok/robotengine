from robotengine import Engine, InputDevice
from robotengine import Node
from robot import Robot


if __name__ == '__main__':
    root = Node("Root")
    
    robot = Robot()
    root.add_child(robot)

    engine = Engine(root, frequency=1, input_devices=[])
    engine.print_tree()
    engine.run()


