"""AHSER Controller Node Skeleton."""

import rclpy
from rclpy.node import Node


class AHSERController(Node):
    """Skeleton controller node for the AHSER robot platform."""

    def __init__(self):
        super().__init__('ahser_controller')
        self.get_logger().info('AHSER controller node initialized (skeleton).')


def main(args=None):
    rclpy.init(args=args)
    node = AHSERController()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
