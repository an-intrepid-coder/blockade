class Camera:
    def __init__(self, xy_tuple):
        self.xy_tuple = xy_tuple
        self.offset_xy_tuple = None

    def set(self, xy_tuple):
        self.xy_tuple = xy_tuple

    def set_offset(self, xy_tuple):
        self.offset_xy_tuple = xy_tuple

    def has_offset(self) -> bool:
        return self.offset_xy_tuple is not None

    def clear_offset(self):
        self.offset_xy_tuple = None
