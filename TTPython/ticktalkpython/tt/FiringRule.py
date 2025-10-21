from enum import Enum
from Clock import TTClock, TTClockSpec

import SQ

import DebugLogger

logger = DebugLogger.get_logger('FiringRule')


class TTFiringRuleType(Enum):
    '''
    An enumeration for the base type of a firing rule. There is a more
    specification for firing rules in ``TTFiringRule``
    '''
    Strict = 0
    Timed = 1
    TimedRetrigger = 2
    SequentialRetrigger = 3

    # experimental
    Immediate = 4
    Deadline = 5


class TTFiringRule():
    '''
    Full description of a firing rule

    :param rule_type: The type of the firing rule
    :type rule_type: TTFiringRuleType
    :param pattern: The input/ouput pattern the SQ follows
    :type pattern: TTSQPattern
    :param firing_rule_args: A set of arguments for configuring the firing rule,
        in a dictionary. The members depend on the rule_type
    :type firing_rule_args: dict
    :param is_sequential: Boolean indicating if this SQ needs to be on
        sequential/chronological inputs. Defaults to False
    :type is_sequential: bool
    :param use_deadline: Boolean indicating if this SQ uses a deadline or not.
        Exact specifications should be included within the firing_rule_args
        dictionary. Defaults to False
    :type use_deadline: bool
    '''
    def __init__(self,
                 rule_type,
                 firing_rule_args,
                 pattern,
                 is_sequential=False,
                 use_deadline=False):
        assert isinstance(
            rule_type, SQ.TTFiringRuleType
        ), f'firing rule type must be of type {SQ.TTFiringRuleType}'
        self.rule_type = rule_type
        self.is_sequential = is_sequential
        self.use_deadline = use_deadline
        self.pattern = pattern

        if rule_type == SQ.TTFiringRuleType.TimedRetrigger:
            self.configureTimedRetriggering(firing_rule_args)

        if rule_type == SQ.TTFiringRuleType.Deadline:
            self.configureDeadlineTriggering(firing_rule_args)

    def configureTimedRetriggering(self, firing_rule_args_dict):
        self.clock = None
        self.period = 1
        self.phase = 0
        for key in firing_rule_args_dict.keys():
            if key == 'streaming_clock':
                self.clock = firing_rule_args_dict[
                    key]  #this should be a TTClockSpec
            elif key == 'streaming_period':
                self.period = firing_rule_args_dict[
                    key]  #this is in terms of the attached clock; else we assume it's the root clock
            elif key == 'streaming_phase':
                self.phase = firing_rule_args_dict[
                    key]  #this should be within [0, period)

        if not self.clock:
            self.clock = TTClock.root()
            # must be a better way to access this. It should be replaced
            # at runtime with a clock hosted by the ensemble (or its processes)

        assert self.phase % self.period == self.phase, f'phase must be within [0, period={self.period}'

        self.period = self.period * self.clock.root_ticks_per_tick(
        )  #store these w.r.t. the root domain to make delays and such easier to calculate
        self.phase = self.phase * self.clock.root_ticks_per_tick(
        )  #how does phase get modulated?

        if not self.clock.is_root():
            logger.error(
                'Please only use the root clock for stream generation; tracing to root'
            )
            c = self.clock
            while not c.is_root():
                c = c.parent()
            self.clock = c

        self.clockspec = TTClockSpec.fromClock(self.clock)

    def configureDeadlineTriggering(self, firing_rule_args_dict):
        self.clock = None
        for key in firing_rule_args_dict.keys():
            if key == 'streaming_clock':
                self.clock = firing_rule_args_dict[
                    key]  #this should be a TTClockSpec

        if not self.clock:
            self.clock = TTClock.root()

        self.clockspec = TTClockSpec.fromClock(self.clock)

    def update_clock(self, clocks):
        '''
        Update the clock being used for this firing rule to match the runtime
        environment, mainly for reading the current time when determining the
        next stream sampling time

        :param clocks: A list of clocks provided by the runtime to choose from
        :type clocks: list(TTClock)
        '''
        if self.rule_type != SQ.TTFiringRuleType.TimedRetrigger:
            #are there other cases that require use of a clock?
            return

        updated_clock = False
        #search the clocks until we find one with an equivalent specification (TTClockSpec)
        for c in clocks:
            if TTClockSpec.fromClock(c) == TTClockSpec.fromClock(self.clock):
                logger.debug('Replaced clock %s with %s in sync sq' %
                             (self.clock, c))
                self.clock = c
                updated_clock = True
                logger.debug('current time on this clock is %d' % c.now())

        if not updated_clock:
            logger.warning('Could not find a clock to update for SQ %s' %
                           self.sq_name)
            logger.warning(clocks)
            logger.warning(self.clock)
