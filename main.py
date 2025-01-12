from robotengine import Engine, InputDevice
from robotengine import Node
from robot import Robot


if __name__ == '__main__':
    root = Node("Root")
    
    robot = Robot(warn=True)
    root.add_child(robot)

    root.print_tree()

    engine = Engine(root, frequency=-1, input_devices=[InputDevice.GAMEPAD])
    engine.run()


