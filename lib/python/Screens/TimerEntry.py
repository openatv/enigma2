from Screens.Timers import InstantRecordTimerEdit, RecordTimerEdit, TimerLog as TimerLogNew


class TimerEntry(RecordTimerEdit):
	def __init__(self, session, timer):
		RecordTimerEdit.__init__(self, session, timer)


class TimerLog(TimerLogNew):
	def __init__(self, session, timer):
		TimerLogNew.__init__(self, session, timer)


class InstantRecordTimerEntry(InstantRecordTimerEdit):
	def __init__(self, session, timer, zap=0, zaprecord=0):
		InstantRecordTimerEdit.__init__(self, session, timer, zap, zaprecord)
