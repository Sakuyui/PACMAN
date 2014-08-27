from pacman.model.routing_tables.multicast_routing_table import \
    MulticastRoutingTable
from pacman.operations.router_algorithms.abstract_router_algorithm \
    import AbstractRouterAlgorithm
from pacman.utilities.progress_bar import ProgressBar
from pacman import exceptions

import logging
from spinn_machine.multicast_routing_entry import MulticastRoutingEntry

logger = logging.getLogger(__name__)


class BasicDijkstraRouting(AbstractRouterAlgorithm):
    """ An routing algorithm that can find routes for subedges between\
        subvertices in a partitioned_graph that have been placed on a
        machine by the use of a dijkstra shortest path algorithm
    """

    BW_PER_ROUTE_ENTRY = 0.01
    MAX_BW = 250

    def __init__(self, k=1, l=0, m=0, bw_per_route_entry=BW_PER_ROUTE_ENTRY,
                 max_bw=MAX_BW):
        """constructor for the
        pacman.operations.router_algorithms.DijkstraRouting.DijkstraRouting

        <params to be implemented when done>
        """
        AbstractRouterAlgorithm.__init__(self)
        self._k = k
        self._l = l
        self._m = m
        self._bw_per_route_entry = bw_per_route_entry
        self._max_bw = max_bw

    def route(self, routing_info_allocation, placements, machine,
              partitioned_graph):
        """ Find routes between the subedges with the allocated information,
            placed in the given places

        :param routing_info_allocation: The allocated routing information
        :type routing_info_allocation:\
                :py:class:`pacman.model.routing_info.routing_info.RoutingInfo`
        :param placements: The placements of the subedges
        :type placements:\
                    :py:class:`pacman.model.placements.placements.Placements`
        :param machine: The machine through which the routes are to be found
        :type machine: :py:class:`spinn_machine.machine.Machine`
        :param partitioned_graph: the partitioned_graph object
        :type partitioned_graph:
        pacman.partitioned_graph.partitioned_graph.PartitionedGraph
        :return: The discovered routes
        :rtype:
        :py:class:`pacman.model.routing_tables.multicast_routing_tables.MulticastRoutingTables`
        :raise pacman.exceptions.PacmanRoutingException: If something\
                   goes wrong with the routing
        """
        #set up basic data structures
        nodes_info = self._initiate_node_info(machine)
        dijkstra_tables = self._initiate_dijkstra_tables(machine)
        self._update_all_weights(nodes_info, machine)

        #each subvertex represents a core in the board
        progress = ProgressBar(len(list(placements.placements)),
                               "on creating routing entries for each subvertex")
        for placement in placements.placements:
            subvert = placement.subvertex
            out_going_sub_edges = \
                partitioned_graph.outgoing_subedges_from_subvertex(subvert)

            dest_processors = []
            subedges_to_route = list()
            xs, ys, ps = placement.x, placement.y, placement.p

            for subedge in out_going_sub_edges:
                destination_subvetex = subedge.post_subvertex
                destination_placement = \
                    placements.get_placement_of_subvertex(destination_subvetex)

                chip = machine.get_chip_at(destination_placement.x,
                                           destination_placement.y)
                processor = chip.get_processor_with_id(destination_placement.p)
                dest_processors.append({'processor': processor, 'chip': chip})
                subedges_to_route.append(subedge)

            if len(dest_processors) != 0:
                self._update_all_weights(nodes_info, machine)
                self._reset_tables(dijkstra_tables)
                xa, ya = xs, ys
                dijkstra_tables[(xa, ya)]["activated?"] = True
                dijkstra_tables[(xa, ya)]["lowest cost"] = 0
                self._propagate_costs_until_reached_destinations(
                    dijkstra_tables, nodes_info, xa, ya, dest_processors, xs,
                    ys)

            for subedge in subedges_to_route:
                subedge_routing_info = \
                    routing_info_allocation.\
                    get_subedge_information_from_subedge(subedge)
                dest = subedge.post_subvertex
                placement = placements.get_placement_of_subvertex(dest)
                xd, yd, pd = placement.x, placement.y, placement.p
                self._retrace_back_to_source(
                    xd, yd, nodes_info, dijkstra_tables, subedge_routing_info,
                    pd)
            progress.update()
        progress.end()
        return self._routing_tables

    def _initiate_node_info(self, machine):
        """private method DO NOT CALL FROM OUTSIDE BASIC DIJKSTRA ROUTING. \
        used for setting up a dictionary which contains data for each chip in \
        the machine

        :param machine: the machine object
        :type machine: spinn_machine.machine.Machine
        :return: nodes_info dictionary
        :rtype: dict
        :raise None: this method does not raise any known exceptions
        """
        nodes_info = dict()
        for chip in machine.chips:
            x, y = chip.x, chip.y
            # get_neighbours should return a list of
            # dictionaries of 'x' and 'y' values
            nodes_info[(x, y)] = dict()
            neighbours = list(machine.get_chip_at(x, y).router.links)

            nodes_info[(x, y)]["neighbours"] = list()
            for source_id in range(6):
                exist_link = self.locate_link_with_id(source_id, neighbours)
                nodes_info[(x, y)]["neighbours"].append(exist_link)

            nodes_info[(x, y)]["bws"] = []

            nodes_info[(x, y)]["weights"] = []

            for i in range(len(nodes_info[(x, y)]["neighbours"])):

                nodes_info[(x, y)]["weights"].append(None)

                if nodes_info[(x, y)]["neighbours"][i] is None:

                    nodes_info[(x, y)]["bws"].append(None)

                else:

                    nodes_info[(x, y)]["bws"].append(self._max_bw)
        return nodes_info

    @staticmethod
    def locate_link_with_id(link_id, links):
        for link in links:
            if link.source_link_id == link_id:
                return link
        return None

    @staticmethod
    def _initiate_dijkstra_tables(machine):
        """ private method DO NOT CALL FROM OUTSIDE BASIC DIJKSTRA ROUTING. \
        used to set up the Dijkstra's table which includes if you've reached a \
        given node

        :param machine: the machine object
        :type machine: the spinn_machine.machine.Machine object
        :return the  Dijkstra's table dictionary
        :rtype: dict
        :raise None: this method does not raise any known exception
        """

        dijkstra_tables = dict()  # Holds all the information about nodes within
                                  #  one full run of Dijkstra's algorithm

        for chip in machine.chips:
            x, y = chip.x, chip.y
            dijkstra_tables[(x, y)] = dict()  # Each node has a
                                                      # dictionary, or 'table'

            dijkstra_tables[(x, y)]["lowest cost"] = None
            dijkstra_tables[(x, y)]["activated?"] = False
        return dijkstra_tables

    def _update_all_weights(self, nodes_info, machine):
        """private method DO NOT CALL FROM OUTSIDE BASIC DIJKSTRA ROUTING. \
        used by the routing algorithum to change the weights of the nebourign \
        nodes

        :param nodes_info: the node info dictonary
        :param machine: the machine python object that represnets the strcuture\
        of the machine
        :type nodes_info: dict
        :type machine 'py:class':spinn_machine.machine.Machine
        :return None
        :rtype: None
        :raise None: this method does not raise any known exception
        """
        for key in nodes_info.keys():
            if nodes_info[key] is not None:
                self._update_neaubiours_weights(nodes_info, machine, key)

    def _update_neaubiours_weights(self, nodes_info, machine, key):
        """private method DO NOT CALL FROM OUTSIDE BASIC DIJKSTRA ROUTING. \
        used by the routing algorithm to change the weights of the neighbouring\
        nodes

        :param nodes_info: the node info dictionary
        :param machine: the machine python object that represents the structure\
        of the machine
        :param key: the identifier to the object in nodes_info
        :type key: str
        :type nodes_info: dict
        :type machine 'py:class':spinn_machine.machine.Machine
        :return None
        :rtype: None
        :raise None: this method does not raise any known exception
        """
        for n in range(len(nodes_info[key]["neighbours"])):
            if nodes_info[key]["neighbours"][n] is not None:
                neighbour = nodes_info[key]["neighbours"][n]
                xn, yn = neighbour.destination_x, neighbour.destination_y
                nodes_info[key]["weights"][n] = \
                    self._get_weight(
                        machine.get_chip_at(xn, yn).router,
                        nodes_info[key]["bws"][n],
                        self._get_routing_table_for_chip(xn, yn))

    def _get_routing_table_for_chip(self, chip_x, chip_y):
        """helper method to retrieve a routing table
        
        :param chip_x: the x coord for a chip
        :param chip_y: the y coord for a chip
        :type chip_x: int
        :type chip_y: int
        :return a routing table
        :rtype: pacman.routing_tables.RoutingTable
        :raise None: this method does not raise any known exception

        """
        table = self._routing_tables.get_routing_table_for_chip(chip_x, chip_y)
        if table is not None:
            return table
        else:
            chip_routing_table = MulticastRoutingTable(chip_x, chip_y)
            self._routing_tables.add_routing_table(chip_routing_table)
            return chip_routing_table

    def _get_weight(self, router, bws, routing_table):
        """private method DO NOT CALL FROM OUTSIDE BASIC DIJKSTRA ROUTING. \
        used by the routing algorithm to determine the weight based on basic
        heuristics

        :param router: the router to assess the weight of
        :param bws: the basic weight of the source node
        :param routing_table: the routing table object for this router
        :type router: spinn_machine.router.Router
        :type bws: int
        :type routing_table:
    pacman.model.routing_tables.multicast_routing_table.MulticastRoutingTable
        :return weight of this router
        :rtype: int
        :raise None: does not raise any known exception
        """
        free_entries = \
            router.ROUTER_DEFAULT_AVAILABLE_ENTRIES - \
            routing_table.number_of_entries

        q = float(self._l *
                  (1 / float(free_entries) - 1 /
                   float(router.ROUTER_DEFAULT_AVAILABLE_ENTRIES)))

        t = self._m * (1 / float(bws) - 1 / float(self._max_bw))

        weight = self._k + q + t
        return weight

    @staticmethod
    def _reset_tables(dijkstra_tables):
        """private method DO NOT CALL FROM OUTSIDE BASIC DIJKSTRA ROUTING. \
        used to reset the dijsktra tables for a new path search

        :param dijkstra_tables: the dictory object for the dijkstra-tables
        :type dijkstra_tables: dict
        :return: None
        :rtype: None
        :raise None: this method does not raise any known exception
        """
        for key in dijkstra_tables.keys():
            dijkstra_tables[key]["lowest cost"] = None
            dijkstra_tables[key]["activated?"] = False

    def _propagate_costs_until_reached_destinations(
            self, dijkstra_tables, nodes_info, xa, ya, dest_processors, xs, ys):
        """private method DO NOT CALL FROM OUTSIDE BASIC DIJKSTRA ROUTING. \
        used to propagate the weights till the destination nodes of the source\
        nodes are reaced
         
         :param dijkstra_tables: the dictionary object for the dijkstra-tables
         :param nodes_info: the dictionary object for the nodes inside a route \
         scope
         :param xa:
         :param ya:
         :param dest_processors:
         :param xs:
         :param ys:
         :type dijkstra_tables: dict
         :type nodes_info: dict
         :type xa: int
         :type ya: int
         :type dest_processors:
         :type xs: int
         :type ys: int
         :return: None
         :rtype: None
         :raise PacmanRoutingException: when the destination node could not be\
         reached from this soruce node.
        """

        destination_processors_left_to_find = dest_processors
        # Iterate only if the destination node hasn't been activated
        while not (len(destination_processors_left_to_find) == 0):
            # PROPAGATE!
            for i in range(len(nodes_info[(xa, ya)]["neighbours"])):
                neighbour = nodes_info[(xa, ya)]["neighbours"][i]
                weight = nodes_info[(xa, ya)]["weights"][i]
                # "neighbours" is a list of 6 dictionaries or None objects.
                # There is a None object where there is no connection to
                # that neighbour.
                if (neighbour is not None) and not (neighbour.destination_x == xs
                                                    and neighbour.destination_y == ys):

                    # These variables change with every look at a new neighbour
                    xn, yn = neighbour.destination_x, neighbour.destination_y
                    self._update_neighbour(dijkstra_tables, xn, yn, xa, ya,
                                           xs, ys, weight)

            # This cannot be done in the above loop, since when a node
            # becomes activated the rest of the costs cannot be retrieved, and
            #  a new partitionable_graph lowest cost cannot be found
            graph_lowest_cost = None  # This is the lowest cost across ALL
                                      # unactivated nodes in the partitionable_graph.

            # Find the next node to be activated
            for key in dijkstra_tables.keys():
                # Don't continue if the node hasn't even been touched yet
                if (dijkstra_tables[key]["lowest cost"] is not None
                    and not dijkstra_tables[key]["activated?"]
                    and (dijkstra_tables[key]["lowest cost"] < graph_lowest_cost
                         and graph_lowest_cost is not None
                         or (graph_lowest_cost is None))):
                            graph_lowest_cost = \
                                dijkstra_tables[key]["lowest cost"]
                            xa, ya = int(key[0]), int(key[1])
    # Set the next activated node as the unactivated node with the
    #  lowest current cost

            dijkstra_tables[(xa, ya)]["activated?"] = True

            # If there were no unactivated nodes with costs,
            # but the destination was not reached this iteration,
            # raise an exception
            if graph_lowest_cost is None:
                raise exceptions.PacmanRoutingException(
                    "Destination could not be activated, ending run")

            #check if each destination node left to find has been activated
            for dest_processor in dest_processors:
                xd = dest_processor['chip'].x
                yd = dest_processor['chip'].y
                if dijkstra_tables[(xd, yd)]["activated?"]:
                    destination_processors_left_to_find.remove(dest_processor)

    @staticmethod
    def _update_neighbour(dijkstra_tables, xn, yn, xa, ya, xs, ys, weight):
        """private method DO NOT CALL FROM OUTSIDE BASIC DIJKSTRA ROUTING. \
        used to update the lowest cost for each neigbhour of a node

        :param dijkstra_tables:
        :param xa:
        :param ya:
        :param xs:
        :param ys:
        :param xn:
        :param yn:
        :param weight:
        :type dijkstra_tables:
        :type xa:
        :type ya:
        :type xs:
        :type ys:
        :type xn:
        :type yn:
        :type weight:
        :return:
        :rtype:
        :raise PacmanRoutingException: when the algoerithum goes to a node that\
        doesnt exist in the machine or the node's cost was set too low.
        """
        # Only try to update if the neighbour is within the partitionable_graph
        #  and the cost if the node hasn't already been activated
        # and the lowest cost if the new cost is less, or if
        # there is no current cost
        neighbour_exists = (xn, yn) in dijkstra_tables.keys()
        neighbour_activated = dijkstra_tables[(xn, yn)]["activated?"]
        chip_lowest_cost = dijkstra_tables[(xa, ya)]["lowest cost"]
        neighbour_lowest_cost = dijkstra_tables[(xn, yn)]["lowest cost"]
        if (neighbour_exists and not neighbour_activated and
            ((chip_lowest_cost + weight) < neighbour_lowest_cost
             or (neighbour_lowest_cost is None))):
                #update dijkstra table
                dijkstra_tables[(xn, yn)]["lowest cost"] = \
                    float(chip_lowest_cost + weight)
        elif not neighbour_exists:
            raise exceptions.PacmanRoutingException(
                "Tried to propagate to ({}, {}), which is not in the partitionable_graph:"
                " remove non-existent neighbours".format(xn, yn))

        if (dijkstra_tables[(xn, yn)]["lowest cost"] == 0) \
                and (xn != xs or yn != ys):
            raise exceptions.PacmanRoutingException(
                "!!!Cost of non-source node ({}, {}) was set to zero!!!"
                .format(xn, yn))
            
    def _retrace_back_to_source(self, xd, yd, nodes_info,
                                dijkstra_tables, subedge_routing_info, pd):
        """private method DO NOT CALL FROM OUTSIDE BASIC DIJKSTRA ROUTING. \
        
        :param xd:
        :param yd:
        :param nodes_info:
        :param dijkstra_tables:
        :param subedge_routing_info:
        :param pd:
        :type xd:
        :type yd:
        :type nodes_info:
        :type dijkstra_tables:
        :type subedge_routing_info:
        :type pd:
        :return: the next coords to look into
        :rtype: int int
        :raise PacmanRoutingException: when the algorithum doesnt find a next\
         point to search from. AKA, the neighbours of a chip do not have a \
         cheaper cost than the node itslef, but the node is not the destination\
         or when the algorithum goes to a node thats not cosndiered in the \
         weighted search
        """
        # Set the tracking node to the destination to begin with
        xt, yt = xd, yd
        # move 6 accross to get it past edges, then move up the steps to reach
        # the processor which receives the packet
        routing_entry_route_processors = [pd]
        routing_entry_route_links = list()
        #check that the key hasnt already been used
        key = subedge_routing_info.key
        mask = subedge_routing_info.mask
        routing_table = self._get_routing_table_for_chip(xd, yd)
        #check if an other_entry with the same key mask combo exists
        other_entry = routing_table.get_multicast_routing_entry_by_key(key,
                                                                       mask)
        if other_entry is not None:
            merged_entry = \
                self._merge_entries(other_entry, routing_entry_route_processors,
                                    key, mask, routing_entry_route_links,
                                    routing_table, False)
            previous_routing_entry = merged_entry
        else:
            entry = MulticastRoutingEntry(key, mask,
                                          routing_entry_route_processors,
                                          routing_entry_route_links, False)
            routing_table.add_mutlicast_routing_entry(entry)
            previous_routing_entry = entry

        while dijkstra_tables[(xt, yt)]["lowest cost"] != 0:

            xcheck, ycheck = xt, yt

            neighbours = nodes_info[(xt, yt)]["neighbours"]
            neighbour_index = 0
            added_an_entry = False
            length = len(neighbours)
            while not added_an_entry and neighbour_index < len(neighbours):
                neighbour = neighbours[neighbour_index]
                if neighbour is not None:
                    # "neighbours" is a list of up to 6 dictionaries.
                    # xnr and ynr for 'x neighbour retrace',
                    # 'y neighbour retrace'.
                    xnr, ynr = neighbour.destination_x, neighbour.destination_y
                    neighbour_routing_table = \
                        self._get_routing_table_for_chip(xnr, ynr)
                    # Only check if it can be a preceding node if it actually
                    # exists
                    if (xnr, ynr) in dijkstra_tables.keys():
                        dijkstra_table_key = (xnr, ynr)
                        lowest_cost = \
                            dijkstra_tables[dijkstra_table_key]["lowest cost"]
                        if lowest_cost is not None:
                            xt, yt, previous_routing_entry, added_an_entry = \
                                self._create_routing_entry(
                                    xnr, ynr, dijkstra_tables,
                                    neighbour_index, nodes_info,
                                    neighbour_routing_table, xt, yt,
                                    subedge_routing_info,
                                    previous_routing_entry)
                    else:
                        print xnr, ynr
                        raise exceptions.PacmanRoutingException(
                            "Tried to trace back to node not in "
                            "partitionable_graph: remove non-existent"
                            " neighbours")
                neighbour_index += 1

            if xt == xcheck and yt == ycheck:
                raise exceptions.PacmanRoutingException(
                    "Iterated through all neighbours of tracking node but"
                    " did not find a preceding node! Consider increasing "
                    "acceptable discrepancy between sought traceback cost"
                    " and actual cost at node. Terminating...")
        return xt, yt

    @staticmethod
    def _merge_entries(other_entry, routing_entry_route_processors, defaultable,
                       key, mask, routing_entry_route_links, routing_table):
        """private method DO NOT CALL FROM OUTSIDE BASIC DIJKSTRA ROUTING. \

        :param other_entry:
        :param routing_entry_route_processors:
        :param routing_entry_route_links:
        :param routing_table:
        :param defaultable:
        :param key:
        :param mask:
        :type other_entry:
        :type routing_entry_route_processors:
        :type routing_entry_route_links:
        :type routing_table:
        :type defaultable:
        :type key:
        :type mask:
        :return a new entry which is the merged result of two entries
        :rtype: spinn_machine.multicast_routing_entry
        :raise None: this method does not raise any known exception
        """
        multi_cast_routing_entry = \
            MulticastRoutingEntry(key, mask, routing_entry_route_processors,
                                  routing_entry_route_links, defaultable)
        new_entry = other_entry.merge(multi_cast_routing_entry)
        routing_table.remove_multicast_routing_entry(other_entry)
        routing_table.add_mutlicast_routing_entry(new_entry)
        return new_entry

    def _create_routing_entry(self, xnr, ynr, dijkstra_tables, n,
                              nodes_info, router_table, xt, yt, edge_info,
                              previous_routing_entry):
        """private method DO NOT CALL FROM OUTSIDE BASIC DIJKSTRA ROUTING. \
        
        :param xnr:
        :param ynr:
        :param dijkstra_tables:
        :param n
        :param nodes_info:
        :param router_table:
        :param xt:
        :param yt:
        :param edge_info:
        :param previous_routing_entry:
        :type xnr:
        :type ynr:
        :type dijkstra_tables:
        :type n
        :type nodes_info:
        :type router_table:
        :type xt:
        :type yt:
        :type edge_info:
        :type previous_routing_entry:
        :return xt, yt, previous_routing_entry, made_an_entry
        :rtype: int, int, spinn_machine.multicast_routing_entry, bool
        :raise PacmanRoutingException: when the bandwidth of a router is beyond\
        respectable parameters
        """

        # Set the direction of the routing other_entry as that which
        # is from the preceding node to the current tracking node
        # xnr, ynr are the 'old' coordinates since they are from the
        # preceding node. xt and yt are the 'new' coordinates since
        # they are where the router should send the packet to
        bin_direction, dec_direction = self._get_direction(n)
        made_an_entry = False
        #determine if this entry is going to be defaultable
        entry_is_defaultable = False
        if bin_direction in previous_routing_entry.link_ids:
            entry_is_defaultable = True

        neighbour_weight = nodes_info[(xnr, ynr)]["weights"][dec_direction]
        chip_sought_cost = \
            dijkstra_tables[(xt, yt)]["lowest cost"] - neighbour_weight
        neighbours_lowest_cost = dijkstra_tables[(xnr, ynr)]["lowest cost"]
        #print ("Checking node (%d, %d) with sought cost %s and actual
        # cost %s") % (xnr, ynr, chip_sought_cost,
        # dijkstra_tables[xnr][ynr]["lowest cost"])

        if neighbours_lowest_cost is not None and \
           abs(neighbours_lowest_cost - chip_sought_cost) < 0.00000000001:
            #get other routing table and entry
            other_routing_table = \
                self._get_routing_table_for_chip(xnr, ynr)
            edge_key, edge_mask = edge_info.key, edge_info.mask
            other_routing_table_entry = other_routing_table.\
                get_multicast_routing_entry_by_key(edge_key, edge_mask)
            if other_routing_table_entry is not None:
                #already has an other_entry, check if mergable,
                #  if not then throw error, therefore should only ever
                # have 1 other_entry
                if other_routing_table_entry.key == edge_key:
                    #merge routes
                    merged_entry = self._merge_entries(
                        other_routing_table_entry, (), entry_is_defaultable,
                        edge_key, edge_mask, list().append(bin_direction),
                        router_table)
                    previous_routing_entry = merged_entry
            else:
                entry = MulticastRoutingEntry(
                    edge_key, edge_mask, (), [bin_direction],
                    entry_is_defaultable)
                router_table.add_mutlicast_routing_entry(entry)
                previous_routing_entry = entry
            made_an_entry = True

            # Finally move the tracking node
            xt, yt = xnr, ynr

            nodes_info[(xnr, ynr)]["bws"][dec_direction] -= \
                self._bw_per_route_entry  # TODO arbitrary

            if nodes_info[(xnr, ynr)]["bws"][dec_direction] < 0:
                print ("Bandwidth overused from ({}, {}) in direction {}! to "
                       "({}, {})".format(xnr, ynr, bin_direction, xt, yt))

                raise exceptions.PacmanRoutingException(
                    "Bandwidth overused as described above! Terminating...")
        return xt, yt, previous_routing_entry, made_an_entry

    @staticmethod
    def _get_direction(neighbour_position):
        """private method, do not call from outside dijskra routing\

        used to detmerine the direction of a link to go down

        :param neighbour_position: the position the neighbour is at
        :type neighbour_position: int
        :return the binary position and the integer verison of the route
        :rtype: int int
        :raise None: this method does not raise any known exceptions
        """

        bin_direction = None
        dec_direction = None
        if neighbour_position == 0:
            bin_direction = 1 << 3  # East
            dec_direction = 3
        elif neighbour_position == 1:
            bin_direction = 1 << 4  # North East
            dec_direction = 4
        elif neighbour_position == 2:
            bin_direction = 1 << 5  # North
            dec_direction = 5
        elif neighbour_position == 3:
            bin_direction = 1 << 0  # West
            dec_direction = 0
        elif neighbour_position == 4:
            bin_direction = 1 << 1  # South West
            dec_direction = 1
        elif neighbour_position == 5:
            bin_direction = 1 << 2  # South
            dec_direction = 2
        return bin_direction, dec_direction

    @staticmethod
    def _has_same_route(processors, links, entry):
        """ private method, not to be called outside dijskra routing

        :param processors: the list of processors that a routing entry has gone\
         down
        :param links: the list of links to which a routing entry has gone down
        :param entry: the other entry to compare against
        :type processors: list of ints
        :type links: list of ints
        :type entry: spinn_machine.multicast_routing_entry.MultcastRoutingEntry
        :return true if the links and processors are the same \
        (same outgoing route)
        :rtype: bool
        :raise None: this method does not raise any known exception

        """
        if entry.processors_ids == processors and entry.link_ids == links:
            return True
        else:
            return False