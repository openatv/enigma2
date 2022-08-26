from Screens.Timers import RecordTimerOverview, ConflictTimerOverview


class TimerEditList(RecordTimerOverview):
	def __init__(self, session):
		RecordTimerOverview.__init__(self, session)


class TimerSanityConflict(ConflictTimerOverview):
	def __init__(self, session, timers):
		ConflictTimerOverview.__init__(self, session, timers)
