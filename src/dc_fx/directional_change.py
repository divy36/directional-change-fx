"""Online directional-change detection with a fixed initial anchor."""


class Detector:
    def __init__(self, first_price):
        self.anchor = first_price
        self.extreme = first_price
        self.trend = 0
        self.index = -1
        self.extreme_index = 0
        self.event_origin_index = 0

    def update(self, price, up, down):
        self.index += 1
        event = 0
        if self.trend == 0:
            if (price - self.anchor) / self.anchor >= up:
                event = 1
            elif (self.anchor - price) / self.anchor >= down:
                event = -1
        elif self.trend == 1:
            if price > self.extreme:
                self.extreme = price
                self.extreme_index = self.index
            elif (self.extreme - price) / self.extreme >= down:
                event = -1
        else:
            if price < self.extreme:
                self.extreme = price
                self.extreme_index = self.index
            elif (price - self.extreme) / self.extreme >= up:
                event = 1
        if event:
            self.event_origin_index = self.extreme_index
            self.extreme_index = self.index
            self.trend = event
            self.extreme = price
        return event
