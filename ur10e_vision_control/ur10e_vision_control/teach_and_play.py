import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
import threading

class TeachNode(Node):
    def __init__(self):
        super().__init__('teach_node')
        
        # Subscribe to read the angles (Phase 1)
        self.subscription = self.create_subscription(
            JointState,
            '/joint_states',
            self.joint_callback,
            10)
            
        # Publish to command the arm (Phase 2)
        self.publisher = self.create_publisher(
            JointTrajectory, 
            '/joint_trajectory_controller/joint_trajectory', 
            10)
            
        self.current_positions = []
        self.saved_waypoints = []
        
        self.input_thread = threading.Thread(target=self.wait_for_input)
        self.input_thread.start()

    def joint_callback(self, msg):
        target_joints = [
            'shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
            'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint'
        ]
        
        extracted = []
        for name in target_joints:
            if name in msg.name:
                idx = msg.name.index(name)
                extracted.append(msg.position[idx])
        
        if len(extracted) == 6:
            self.current_positions = extracted

    def wait_for_input(self):
        print("\n--- TEACH MODE ACTIVE ---")
        print("Move the arm using terminal commands or Gazebo GUI.")
        
        while rclpy.ok():
            user_input = input("Press [Enter] to save waypoint, or type 'play' to execute: ")
            
            if user_input.lower() == 'play':
                print(f"\nFinished teaching! Total waypoints saved: {len(self.saved_waypoints)}")
                self.execute_trajectory()
                # Reset memory so you can record a new path
                self.saved_waypoints = [] 
                print("\nMemory cleared. Ready to teach a new path.")
                
            elif len(self.current_positions) == 6:
                self.saved_waypoints.append(self.current_positions)
                print(f"-> Waypoint {len(self.saved_waypoints)} saved successfully!")
            else:
                print("Waiting for joint data from Gazebo...")

    def execute_trajectory(self):
        if len(self.saved_waypoints) == 0:
            print("No waypoints to play!")
            return

        msg = JointTrajectory()
        msg.joint_names = [
            'shoulder_pan_joint', 'shoulder_lift_joint', 'elbow_joint',
            'wrist_1_joint', 'wrist_2_joint', 'wrist_3_joint'
        ]

        time_between_points = 3.0  # Seconds to travel between each waypoint
        accumulated_time = time_between_points

        # Loop through memory and build the trajectory message
        for angles in self.saved_waypoints:
            point = JointTrajectoryPoint()
            point.positions = angles
            
            # ROS 2 requires time broken into seconds and nanoseconds
            point.time_from_start.sec = int(accumulated_time)
            point.time_from_start.nanosec = int((accumulated_time - int(accumulated_time)) * 1e9)
            
            msg.points.append(point)
            accumulated_time += time_between_points

        print("Publishing trajectory... Watch Gazebo!")
        self.publisher.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    teach_node = TeachNode()
    
    try:
        rclpy.spin(teach_node)
    except KeyboardInterrupt:
        pass
    finally:
        teach_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()

