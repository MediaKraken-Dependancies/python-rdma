#!/usr/bin/python
import rdma.IBA as IBA;

class Path(object):
    """Describe an RDMA path. This also serves to cache the path for cases
    that need it in an AH or other format. Paths should be considered final,
    once construction is finished their content must never change. This is to
    prevent cached data in the path from becoming stale."""

    retries = 0;
    """This is the number of times a MAD will be resent, or the value
    of retry_cnt for a RC QP."""

    def __init__(self,end_port,**kwargs):
        self.end_port = end_port;
        for k,v in kwargs.iteritems():
            setattr(self,k,v);

    def drop_cache(self):
        """Release any cached information stored in the Path"""
        for I in self.__dict__.keys():
            if I.startswith("_cached"):
                self.__delattr__(I);

class IBPath(Path):
    """Describe a path in an IB network with a LRH and GRH and BTH

    Note that our convention is that a path describes the LRH/GRH/BTH header
    fields. So a packet being sent from here should have a path with SGID ==
    self and the path for a received packet should have DGID == self.
    Ditto for [ds]qpn and [DS]LID. Paths for packets received will thus
    have reversed semantics, SGID == remote.

    This includes all relevant addressing information as well as any
    method specific information (ie a UMAD agent_id) required to use
    it with the method in question. Since this includes the BTH information
    it must also include the DQPN if that is requires (eg for unconnected
    communication)"""
    DLID = 0;
    SLID = 0;
    SL = 0;
    pkey = IBA.PKEY_DEFAULT;
    has_grh = False;
    resp_time = 20; # See C13-13.1.1

    # These are only present if the path is going got be used for
    # something connectionless
    # dqpn = 0;
    # sqpn = 0;
    # qkey = 0;

    # Method specific
    # umad_agent_id = None;

    # These are only present if has_grh is True
    # SGID = bytes(16);
    # DGID = bytes(16);
    # hop_limit = 0;
    # traffic_class = 0;
    # flow_label = 0;

    def reverse(self):
        """Reverse this path in-place according to 13.5.4"""
        self.DLID,self.SLID = self.SLID,self.DLID;
        self.dqpn ,self.sqpn = self.sqpn,self.dqpn;
        if self.has_grh:
            self.DGID,self.SGID = self.SGID,self.DGID;
            self.hop_limit = 0xff;
        self.drop_cache();

    @property
    def SGID_index(self):
        """Cache and return the index of the SGID for the associated end_port"""
        try:
            return self._cached_SGID_index;
        except AttributeError:
            self._cached_SGID_index = self.end_port.gids.index(self.SGID);
            return self._cached_SGID_index;
    @SGID_index.setter
    def SGID_index(self,value):
        self.SGID = self.end_port.gids[value];
        self._cached_SGID_index = value;

    @property
    def pkey_index(self):
        """Cache and return the index of the PKey for the associated end_port"""
        try:
            return self._cached_pkey_index;
        except AttributeError:
            self._cached_pkey_index = self.end_port.pkeys.index(self.pkey);
            return self._cached_pkey_index;
    @pkey_index.setter
    def pkey_index(self,value):
        self.pkey = self.end_port.pkeys[value];
        self._cached_pkey_index = value;

    @property
    def SLID_bits(self):
        """Cache and return the LMC portion of the SLID"""
        # FIXME: Don't think this is actually necessary, the mask in done
        # in the kernel, drivers and HW as well. Kept as a placeholder.
        return self.SLID & 0xFF;
    @SLID_bits.setter
    def SLID_bits(self,value):
        self.SLID = value | self.end_port.lid;

    @property
    def packet_life_time(self):
        """Return the packet lifetime value for this path. The lifetime value
        for the path is the expected uni-directional transit time.  If a value
        has not been provided the the port's subnet_timeout is used."""
        try:
            return self._packet_life_time;
        except AttributeError:
            return self.end_port.subnet_timeout;
    @packet_life_time.setter
    def packet_life_time(self,value):
        self._packet_life_time = value;
        return self._packet_life_time;

    @property
    def mad_timeout(self):
        """Return the timeout to use for MADs on this path"""
        try:
            return self._cached_mad_timeout;
        except AttributeError:
            self._cached_mad_timeout = 4.096E-6*(2**(self.packet_life_time+1) +
                                                 2**self.resp_time);
            return self._cached_mad_timeout;

class IBDRPath(IBPath):
    """Describe a directed route path in an IB network with a VL15 packet,
    a LRH and a SMPFormatDirected"""
    drSLID = 0xFFFF;
    drDLID = 0xFFFF;

    def __init__(self,end_port,**kwargs):
        self.DLID = 0xFFFF;
        self.SLID = 0; # FIXME
        self.drPath = bytes(chr(0));
        self.dqpn = 0;
        self.sqpn = 0;
        self.qkey = IBA.IB_DEFAULT_QP0_QKEY;
        IBPath.__init__(self,end_port,**kwargs);

    @property
    def SGID_index(self):
        raise AttributeError();

    @property
    def has_grh(self):
        return False;
