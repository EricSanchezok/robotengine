"""
示例代码

基础用法：

    from robotengine import Node, Engine

    class Robot(Node):
        def __init__(self, name="Robot"):
            super().__init__(name)

        def _ready(self):
            self.rbprint(f"Hello, {self.name}")

        def _process(self, delta):
            self.rbprint(delta)


    if __name__ == "__main__":
        root = Node("Root")

        robot = Robot()

        root.add_child(robot)

        root.print_tree()

        engine = Engine(root, frequency=1, input_devices=[])
        engine.run()

"""