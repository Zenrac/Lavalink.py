class Memory:
    def __init__(self):
        self.reservable = 0
        self.free = 0
        self.used = 0
        self.allocated = 0


class CPU:
    def __init__(self):
        self.cores = 0
        self.system_load = 0.0
        self.lavalink_load = 0.0


class Stats:
    def __init__(self):
        self.playing_players = 0
        self.memory = Memory()
        self.cpu = CPU()
        self.uptime = 0

    def _update(self, data: dict):
        self.playing_players = data.get("playingPlayers", 0)
        self.memory.reservable = data.get("memory", {}).get("reservable", 0)
        self.memory.free = data.get("memory", {}).get("free", 0)
        self.memory.used = data.get("memory", {}).get("used", 0)
        self.memory.allocated = data.get("memory", {}).get("allocated", 0)
        self.cpu.cores = data.get("cpu", {}).get("cores", 0)
        self.cpu.system_load = data.get("cpu", {}).get("systemLoad", 0)
        self.cpu.lavalink_load = data.get("cpu", {}).get("lavalinkLoad", 0)
        self.uptime = data.get("uptime", 0)
        frame_stats = data.get('frameStats', {})
        self.frames_sent = frame_stats.get('sent', -1)
        self.frames_nulled = frame_stats.get('nulled', -1)
        self.frames_deficit = frame_stats.get('deficit', -1)
        self.penalty = Penalty(self)


class Penalty:
    def __init__(self, stats):
        self.player_penalty = stats.playing_players
        self.cpu_penalty = 1.05 ** (100 * stats.cpu.system_load) * 10 - 10
        self.null_frame_penalty = 0
        self.deficit_frame_penalty = 0

        if stats.frames_nulled is not -1:
            self.null_frame_penalty = (1.03 ** (500 * (stats.frames_nulled / 3000))) * 300 - 300
            self.null_frame_penalty *= 2

        if stats.frames_deficit is not -1:
            self.deficit_frame_penalty = (1.03 ** (500 * (stats.frames_deficit / 3000))) * 600 - 600

        self.total = self.player_penalty + self.cpu_penalty + self.null_frame_penalty + self.deficit_frame_penalty
