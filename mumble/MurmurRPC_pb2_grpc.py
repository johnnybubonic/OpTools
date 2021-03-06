# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

import MurmurRPC_pb2 as MurmurRPC__pb2


class V1Stub(object):
  """
  Meta

  """

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.GetUptime = channel.unary_unary(
        '/MurmurRPC.V1/GetUptime',
        request_serializer=MurmurRPC__pb2.Void.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Uptime.FromString,
        )
    self.GetVersion = channel.unary_unary(
        '/MurmurRPC.V1/GetVersion',
        request_serializer=MurmurRPC__pb2.Void.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Version.FromString,
        )
    self.Events = channel.unary_stream(
        '/MurmurRPC.V1/Events',
        request_serializer=MurmurRPC__pb2.Void.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Event.FromString,
        )
    self.ServerCreate = channel.unary_unary(
        '/MurmurRPC.V1/ServerCreate',
        request_serializer=MurmurRPC__pb2.Void.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Server.FromString,
        )
    self.ServerQuery = channel.unary_unary(
        '/MurmurRPC.V1/ServerQuery',
        request_serializer=MurmurRPC__pb2.Server.Query.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Server.List.FromString,
        )
    self.ServerGet = channel.unary_unary(
        '/MurmurRPC.V1/ServerGet',
        request_serializer=MurmurRPC__pb2.Server.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Server.FromString,
        )
    self.ServerStart = channel.unary_unary(
        '/MurmurRPC.V1/ServerStart',
        request_serializer=MurmurRPC__pb2.Server.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.ServerStop = channel.unary_unary(
        '/MurmurRPC.V1/ServerStop',
        request_serializer=MurmurRPC__pb2.Server.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.ServerRemove = channel.unary_unary(
        '/MurmurRPC.V1/ServerRemove',
        request_serializer=MurmurRPC__pb2.Server.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.ServerEvents = channel.unary_stream(
        '/MurmurRPC.V1/ServerEvents',
        request_serializer=MurmurRPC__pb2.Server.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Server.Event.FromString,
        )
    self.ContextActionAdd = channel.unary_unary(
        '/MurmurRPC.V1/ContextActionAdd',
        request_serializer=MurmurRPC__pb2.ContextAction.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.ContextActionRemove = channel.unary_unary(
        '/MurmurRPC.V1/ContextActionRemove',
        request_serializer=MurmurRPC__pb2.ContextAction.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.ContextActionEvents = channel.unary_stream(
        '/MurmurRPC.V1/ContextActionEvents',
        request_serializer=MurmurRPC__pb2.ContextAction.SerializeToString,
        response_deserializer=MurmurRPC__pb2.ContextAction.FromString,
        )
    self.TextMessageSend = channel.unary_unary(
        '/MurmurRPC.V1/TextMessageSend',
        request_serializer=MurmurRPC__pb2.TextMessage.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.TextMessageFilter = channel.stream_stream(
        '/MurmurRPC.V1/TextMessageFilter',
        request_serializer=MurmurRPC__pb2.TextMessage.Filter.SerializeToString,
        response_deserializer=MurmurRPC__pb2.TextMessage.Filter.FromString,
        )
    self.LogQuery = channel.unary_unary(
        '/MurmurRPC.V1/LogQuery',
        request_serializer=MurmurRPC__pb2.Log.Query.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Log.List.FromString,
        )
    self.ConfigGet = channel.unary_unary(
        '/MurmurRPC.V1/ConfigGet',
        request_serializer=MurmurRPC__pb2.Server.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Config.FromString,
        )
    self.ConfigGetField = channel.unary_unary(
        '/MurmurRPC.V1/ConfigGetField',
        request_serializer=MurmurRPC__pb2.Config.Field.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Config.Field.FromString,
        )
    self.ConfigSetField = channel.unary_unary(
        '/MurmurRPC.V1/ConfigSetField',
        request_serializer=MurmurRPC__pb2.Config.Field.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.ConfigGetDefault = channel.unary_unary(
        '/MurmurRPC.V1/ConfigGetDefault',
        request_serializer=MurmurRPC__pb2.Void.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Config.FromString,
        )
    self.ChannelQuery = channel.unary_unary(
        '/MurmurRPC.V1/ChannelQuery',
        request_serializer=MurmurRPC__pb2.Channel.Query.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Channel.List.FromString,
        )
    self.ChannelGet = channel.unary_unary(
        '/MurmurRPC.V1/ChannelGet',
        request_serializer=MurmurRPC__pb2.Channel.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Channel.FromString,
        )
    self.ChannelAdd = channel.unary_unary(
        '/MurmurRPC.V1/ChannelAdd',
        request_serializer=MurmurRPC__pb2.Channel.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Channel.FromString,
        )
    self.ChannelRemove = channel.unary_unary(
        '/MurmurRPC.V1/ChannelRemove',
        request_serializer=MurmurRPC__pb2.Channel.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.ChannelUpdate = channel.unary_unary(
        '/MurmurRPC.V1/ChannelUpdate',
        request_serializer=MurmurRPC__pb2.Channel.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Channel.FromString,
        )
    self.UserQuery = channel.unary_unary(
        '/MurmurRPC.V1/UserQuery',
        request_serializer=MurmurRPC__pb2.User.Query.SerializeToString,
        response_deserializer=MurmurRPC__pb2.User.List.FromString,
        )
    self.UserGet = channel.unary_unary(
        '/MurmurRPC.V1/UserGet',
        request_serializer=MurmurRPC__pb2.User.SerializeToString,
        response_deserializer=MurmurRPC__pb2.User.FromString,
        )
    self.UserUpdate = channel.unary_unary(
        '/MurmurRPC.V1/UserUpdate',
        request_serializer=MurmurRPC__pb2.User.SerializeToString,
        response_deserializer=MurmurRPC__pb2.User.FromString,
        )
    self.UserKick = channel.unary_unary(
        '/MurmurRPC.V1/UserKick',
        request_serializer=MurmurRPC__pb2.User.Kick.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.TreeQuery = channel.unary_unary(
        '/MurmurRPC.V1/TreeQuery',
        request_serializer=MurmurRPC__pb2.Tree.Query.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Tree.FromString,
        )
    self.BansGet = channel.unary_unary(
        '/MurmurRPC.V1/BansGet',
        request_serializer=MurmurRPC__pb2.Ban.Query.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Ban.List.FromString,
        )
    self.BansSet = channel.unary_unary(
        '/MurmurRPC.V1/BansSet',
        request_serializer=MurmurRPC__pb2.Ban.List.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.ACLGet = channel.unary_unary(
        '/MurmurRPC.V1/ACLGet',
        request_serializer=MurmurRPC__pb2.Channel.SerializeToString,
        response_deserializer=MurmurRPC__pb2.ACL.List.FromString,
        )
    self.ACLSet = channel.unary_unary(
        '/MurmurRPC.V1/ACLSet',
        request_serializer=MurmurRPC__pb2.ACL.List.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.ACLGetEffectivePermissions = channel.unary_unary(
        '/MurmurRPC.V1/ACLGetEffectivePermissions',
        request_serializer=MurmurRPC__pb2.ACL.Query.SerializeToString,
        response_deserializer=MurmurRPC__pb2.ACL.FromString,
        )
    self.ACLAddTemporaryGroup = channel.unary_unary(
        '/MurmurRPC.V1/ACLAddTemporaryGroup',
        request_serializer=MurmurRPC__pb2.ACL.TemporaryGroup.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.ACLRemoveTemporaryGroup = channel.unary_unary(
        '/MurmurRPC.V1/ACLRemoveTemporaryGroup',
        request_serializer=MurmurRPC__pb2.ACL.TemporaryGroup.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.AuthenticatorStream = channel.stream_stream(
        '/MurmurRPC.V1/AuthenticatorStream',
        request_serializer=MurmurRPC__pb2.Authenticator.Response.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Authenticator.Request.FromString,
        )
    self.DatabaseUserQuery = channel.unary_unary(
        '/MurmurRPC.V1/DatabaseUserQuery',
        request_serializer=MurmurRPC__pb2.DatabaseUser.Query.SerializeToString,
        response_deserializer=MurmurRPC__pb2.DatabaseUser.List.FromString,
        )
    self.DatabaseUserGet = channel.unary_unary(
        '/MurmurRPC.V1/DatabaseUserGet',
        request_serializer=MurmurRPC__pb2.DatabaseUser.SerializeToString,
        response_deserializer=MurmurRPC__pb2.DatabaseUser.FromString,
        )
    self.DatabaseUserUpdate = channel.unary_unary(
        '/MurmurRPC.V1/DatabaseUserUpdate',
        request_serializer=MurmurRPC__pb2.DatabaseUser.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.DatabaseUserRegister = channel.unary_unary(
        '/MurmurRPC.V1/DatabaseUserRegister',
        request_serializer=MurmurRPC__pb2.DatabaseUser.SerializeToString,
        response_deserializer=MurmurRPC__pb2.DatabaseUser.FromString,
        )
    self.DatabaseUserDeregister = channel.unary_unary(
        '/MurmurRPC.V1/DatabaseUserDeregister',
        request_serializer=MurmurRPC__pb2.DatabaseUser.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.DatabaseUserVerify = channel.unary_unary(
        '/MurmurRPC.V1/DatabaseUserVerify',
        request_serializer=MurmurRPC__pb2.DatabaseUser.Verify.SerializeToString,
        response_deserializer=MurmurRPC__pb2.DatabaseUser.FromString,
        )
    self.RedirectWhisperGroupAdd = channel.unary_unary(
        '/MurmurRPC.V1/RedirectWhisperGroupAdd',
        request_serializer=MurmurRPC__pb2.RedirectWhisperGroup.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )
    self.RedirectWhisperGroupRemove = channel.unary_unary(
        '/MurmurRPC.V1/RedirectWhisperGroupRemove',
        request_serializer=MurmurRPC__pb2.RedirectWhisperGroup.SerializeToString,
        response_deserializer=MurmurRPC__pb2.Void.FromString,
        )


class V1Servicer(object):
  """
  Meta

  """

  def GetUptime(self, request, context):
    """GetUptime returns murmur's uptime.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def GetVersion(self, request, context):
    """GetVersion returns murmur's version.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def Events(self, request, context):
    """Events returns a stream of murmur events.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ServerCreate(self, request, context):
    """
    Servers


    ServerCreate creates a new virtual server. The returned server object
    contains the newly created server's ID.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ServerQuery(self, request, context):
    """ServerQuery returns a list of servers that match the given query.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ServerGet(self, request, context):
    """ServerGet returns information about the given server.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ServerStart(self, request, context):
    """ServerStart starts the given stopped server.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ServerStop(self, request, context):
    """ServerStop stops the given virtual server.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ServerRemove(self, request, context):
    """ServerRemove removes the given virtual server and its configuration.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ServerEvents(self, request, context):
    """ServerEvents returns a stream of events that happen on the given server.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ContextActionAdd(self, request, context):
    """
    ContextActions


    ContextActionAdd adds a context action to the given user's client. The
    following ContextAction fields must be set:
    context, action, text, and user.

    Added context actions are valid until:
    - The context action is removed with ContextActionRemove, or
    - The user disconnects from the server, or
    - The server stops.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ContextActionRemove(self, request, context):
    """ContextActionRemove removes a context action from the given user's client.
    The following ContextAction must be set:
    action
    If no user is given, the context action is removed from all users.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ContextActionEvents(self, request, context):
    """ContextActionEvents returns a stream of context action events that are
    triggered by users.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def TextMessageSend(self, request, context):
    """
    TextMessage


    TextMessageSend sends the given TextMessage to the server.

    If no users, channels, or trees are added to the TextMessage, the message
    will be broadcast the entire server. Otherwise, the message will be
    targeted to the specified users, channels, and trees.
    TextMessageFilter filters text messages on a given server.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def TextMessageFilter(self, request_iterator, context):
    """TextMessageFilter filters text messages for a given server.

    When a filter stream is active, text messages sent from users to the
    server are sent over the stream. The RPC client then sends a message back
    on the same stream, containing an action: whether the message should be
    accepted, rejected, or dropped.

    To activate the filter stream, an initial TextMessage.Filter message must
    be sent that contains the server on which the filter will be active.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def LogQuery(self, request, context):
    """
    Logs


    LogQuery returns a list of log entries from the given server.

    To get the total number of log entries, omit min and/or max from the
    query.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ConfigGet(self, request, context):
    """
    Config


    ConfigGet returns the explicitly set configuration for the given server.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ConfigGetField(self, request, context):
    """ConfigGetField returns the configuration value for the given key.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ConfigSetField(self, request, context):
    """ConfigSetField sets the configuration value to the given value.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ConfigGetDefault(self, request, context):
    """ConfigGetDefault returns the default server configuration.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ChannelQuery(self, request, context):
    """
    Channels


    ChannelQuery returns a list of channels that match the given query.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ChannelGet(self, request, context):
    """ChannelGet returns the channel with the given ID.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ChannelAdd(self, request, context):
    """ChannelAdd adds the channel to the given server. The parent and name of
    the channel must be set.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ChannelRemove(self, request, context):
    """ChannelRemove removes the given channel from the server.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ChannelUpdate(self, request, context):
    """ChannelUpdate updates the given channel's attributes. Only the fields that
    are set will be updated.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def UserQuery(self, request, context):
    """
    Users


    UserQuery returns a list of connected users who match the given query.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def UserGet(self, request, context):
    """UserGet returns information on the connected user, given by the user's
    session or name.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def UserUpdate(self, request, context):
    """UserUpdate changes the given user's state. Only the following fields can
    be changed:
    name, mute, deaf, suppress, priority_speaker, channel, comment.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def UserKick(self, request, context):
    """UserKick kicks the user from the server.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def TreeQuery(self, request, context):
    """
    Tree


    TreeQuery returns a representation of the given server's channel/user
    tree.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def BansGet(self, request, context):
    """
    Bans


    BansGet returns a list of bans for the given server.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def BansSet(self, request, context):
    """BansSet replaces the server's ban list with the given list.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ACLGet(self, request, context):
    """
    ACL


    ACLGet returns the ACL for the given channel.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ACLSet(self, request, context):
    """ACLSet overrides the ACL of the given channel to what is provided.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ACLGetEffectivePermissions(self, request, context):
    """ACLGetEffectivePermissions returns the effective permissions for the given
    user in the given channel.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ACLAddTemporaryGroup(self, request, context):
    """ACLAddTemporaryGroup adds a user to a temporary group.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def ACLRemoveTemporaryGroup(self, request, context):
    """ACLRemoveTemporaryGroup removes a user from a temporary group.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def AuthenticatorStream(self, request_iterator, context):
    """
    Authenticator


    AuthenticatorStream opens an authentication stream to the server.

    There can only be one RPC client with an open Stream. If a new
    authenticator connects, the open connected will be closed.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def DatabaseUserQuery(self, request, context):
    """
    Database


    DatabaseUserQuery returns a list of registered users who match given
    query.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def DatabaseUserGet(self, request, context):
    """DatabaseUserGet returns the database user with the given ID.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def DatabaseUserUpdate(self, request, context):
    """DatabaseUserUpdate updates the given database user.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def DatabaseUserRegister(self, request, context):
    """DatabaseUserRegister registers a user with the given information on the
    server. The returned DatabaseUser will contain the newly registered user's
    ID.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def DatabaseUserDeregister(self, request, context):
    """DatabaseUserDeregister deregisters the given user.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def DatabaseUserVerify(self, request, context):
    """DatabaseUserVerify verifies the that the given user-password pair is
    correct.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def RedirectWhisperGroupAdd(self, request, context):
    """
    Audio


    AddRedirectWhisperGroup add a whisper targets redirection for the given
    user. Whenever a user whispers to group "source", the whisper will be
    redirected to group "target".
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def RedirectWhisperGroupRemove(self, request, context):
    """RemoveRedirectWhisperGroup removes a whisper target redirection for
    the the given user.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_V1Servicer_to_server(servicer, server):
  rpc_method_handlers = {
      'GetUptime': grpc.unary_unary_rpc_method_handler(
          servicer.GetUptime,
          request_deserializer=MurmurRPC__pb2.Void.FromString,
          response_serializer=MurmurRPC__pb2.Uptime.SerializeToString,
      ),
      'GetVersion': grpc.unary_unary_rpc_method_handler(
          servicer.GetVersion,
          request_deserializer=MurmurRPC__pb2.Void.FromString,
          response_serializer=MurmurRPC__pb2.Version.SerializeToString,
      ),
      'Events': grpc.unary_stream_rpc_method_handler(
          servicer.Events,
          request_deserializer=MurmurRPC__pb2.Void.FromString,
          response_serializer=MurmurRPC__pb2.Event.SerializeToString,
      ),
      'ServerCreate': grpc.unary_unary_rpc_method_handler(
          servicer.ServerCreate,
          request_deserializer=MurmurRPC__pb2.Void.FromString,
          response_serializer=MurmurRPC__pb2.Server.SerializeToString,
      ),
      'ServerQuery': grpc.unary_unary_rpc_method_handler(
          servicer.ServerQuery,
          request_deserializer=MurmurRPC__pb2.Server.Query.FromString,
          response_serializer=MurmurRPC__pb2.Server.List.SerializeToString,
      ),
      'ServerGet': grpc.unary_unary_rpc_method_handler(
          servicer.ServerGet,
          request_deserializer=MurmurRPC__pb2.Server.FromString,
          response_serializer=MurmurRPC__pb2.Server.SerializeToString,
      ),
      'ServerStart': grpc.unary_unary_rpc_method_handler(
          servicer.ServerStart,
          request_deserializer=MurmurRPC__pb2.Server.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'ServerStop': grpc.unary_unary_rpc_method_handler(
          servicer.ServerStop,
          request_deserializer=MurmurRPC__pb2.Server.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'ServerRemove': grpc.unary_unary_rpc_method_handler(
          servicer.ServerRemove,
          request_deserializer=MurmurRPC__pb2.Server.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'ServerEvents': grpc.unary_stream_rpc_method_handler(
          servicer.ServerEvents,
          request_deserializer=MurmurRPC__pb2.Server.FromString,
          response_serializer=MurmurRPC__pb2.Server.Event.SerializeToString,
      ),
      'ContextActionAdd': grpc.unary_unary_rpc_method_handler(
          servicer.ContextActionAdd,
          request_deserializer=MurmurRPC__pb2.ContextAction.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'ContextActionRemove': grpc.unary_unary_rpc_method_handler(
          servicer.ContextActionRemove,
          request_deserializer=MurmurRPC__pb2.ContextAction.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'ContextActionEvents': grpc.unary_stream_rpc_method_handler(
          servicer.ContextActionEvents,
          request_deserializer=MurmurRPC__pb2.ContextAction.FromString,
          response_serializer=MurmurRPC__pb2.ContextAction.SerializeToString,
      ),
      'TextMessageSend': grpc.unary_unary_rpc_method_handler(
          servicer.TextMessageSend,
          request_deserializer=MurmurRPC__pb2.TextMessage.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'TextMessageFilter': grpc.stream_stream_rpc_method_handler(
          servicer.TextMessageFilter,
          request_deserializer=MurmurRPC__pb2.TextMessage.Filter.FromString,
          response_serializer=MurmurRPC__pb2.TextMessage.Filter.SerializeToString,
      ),
      'LogQuery': grpc.unary_unary_rpc_method_handler(
          servicer.LogQuery,
          request_deserializer=MurmurRPC__pb2.Log.Query.FromString,
          response_serializer=MurmurRPC__pb2.Log.List.SerializeToString,
      ),
      'ConfigGet': grpc.unary_unary_rpc_method_handler(
          servicer.ConfigGet,
          request_deserializer=MurmurRPC__pb2.Server.FromString,
          response_serializer=MurmurRPC__pb2.Config.SerializeToString,
      ),
      'ConfigGetField': grpc.unary_unary_rpc_method_handler(
          servicer.ConfigGetField,
          request_deserializer=MurmurRPC__pb2.Config.Field.FromString,
          response_serializer=MurmurRPC__pb2.Config.Field.SerializeToString,
      ),
      'ConfigSetField': grpc.unary_unary_rpc_method_handler(
          servicer.ConfigSetField,
          request_deserializer=MurmurRPC__pb2.Config.Field.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'ConfigGetDefault': grpc.unary_unary_rpc_method_handler(
          servicer.ConfigGetDefault,
          request_deserializer=MurmurRPC__pb2.Void.FromString,
          response_serializer=MurmurRPC__pb2.Config.SerializeToString,
      ),
      'ChannelQuery': grpc.unary_unary_rpc_method_handler(
          servicer.ChannelQuery,
          request_deserializer=MurmurRPC__pb2.Channel.Query.FromString,
          response_serializer=MurmurRPC__pb2.Channel.List.SerializeToString,
      ),
      'ChannelGet': grpc.unary_unary_rpc_method_handler(
          servicer.ChannelGet,
          request_deserializer=MurmurRPC__pb2.Channel.FromString,
          response_serializer=MurmurRPC__pb2.Channel.SerializeToString,
      ),
      'ChannelAdd': grpc.unary_unary_rpc_method_handler(
          servicer.ChannelAdd,
          request_deserializer=MurmurRPC__pb2.Channel.FromString,
          response_serializer=MurmurRPC__pb2.Channel.SerializeToString,
      ),
      'ChannelRemove': grpc.unary_unary_rpc_method_handler(
          servicer.ChannelRemove,
          request_deserializer=MurmurRPC__pb2.Channel.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'ChannelUpdate': grpc.unary_unary_rpc_method_handler(
          servicer.ChannelUpdate,
          request_deserializer=MurmurRPC__pb2.Channel.FromString,
          response_serializer=MurmurRPC__pb2.Channel.SerializeToString,
      ),
      'UserQuery': grpc.unary_unary_rpc_method_handler(
          servicer.UserQuery,
          request_deserializer=MurmurRPC__pb2.User.Query.FromString,
          response_serializer=MurmurRPC__pb2.User.List.SerializeToString,
      ),
      'UserGet': grpc.unary_unary_rpc_method_handler(
          servicer.UserGet,
          request_deserializer=MurmurRPC__pb2.User.FromString,
          response_serializer=MurmurRPC__pb2.User.SerializeToString,
      ),
      'UserUpdate': grpc.unary_unary_rpc_method_handler(
          servicer.UserUpdate,
          request_deserializer=MurmurRPC__pb2.User.FromString,
          response_serializer=MurmurRPC__pb2.User.SerializeToString,
      ),
      'UserKick': grpc.unary_unary_rpc_method_handler(
          servicer.UserKick,
          request_deserializer=MurmurRPC__pb2.User.Kick.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'TreeQuery': grpc.unary_unary_rpc_method_handler(
          servicer.TreeQuery,
          request_deserializer=MurmurRPC__pb2.Tree.Query.FromString,
          response_serializer=MurmurRPC__pb2.Tree.SerializeToString,
      ),
      'BansGet': grpc.unary_unary_rpc_method_handler(
          servicer.BansGet,
          request_deserializer=MurmurRPC__pb2.Ban.Query.FromString,
          response_serializer=MurmurRPC__pb2.Ban.List.SerializeToString,
      ),
      'BansSet': grpc.unary_unary_rpc_method_handler(
          servicer.BansSet,
          request_deserializer=MurmurRPC__pb2.Ban.List.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'ACLGet': grpc.unary_unary_rpc_method_handler(
          servicer.ACLGet,
          request_deserializer=MurmurRPC__pb2.Channel.FromString,
          response_serializer=MurmurRPC__pb2.ACL.List.SerializeToString,
      ),
      'ACLSet': grpc.unary_unary_rpc_method_handler(
          servicer.ACLSet,
          request_deserializer=MurmurRPC__pb2.ACL.List.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'ACLGetEffectivePermissions': grpc.unary_unary_rpc_method_handler(
          servicer.ACLGetEffectivePermissions,
          request_deserializer=MurmurRPC__pb2.ACL.Query.FromString,
          response_serializer=MurmurRPC__pb2.ACL.SerializeToString,
      ),
      'ACLAddTemporaryGroup': grpc.unary_unary_rpc_method_handler(
          servicer.ACLAddTemporaryGroup,
          request_deserializer=MurmurRPC__pb2.ACL.TemporaryGroup.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'ACLRemoveTemporaryGroup': grpc.unary_unary_rpc_method_handler(
          servicer.ACLRemoveTemporaryGroup,
          request_deserializer=MurmurRPC__pb2.ACL.TemporaryGroup.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'AuthenticatorStream': grpc.stream_stream_rpc_method_handler(
          servicer.AuthenticatorStream,
          request_deserializer=MurmurRPC__pb2.Authenticator.Response.FromString,
          response_serializer=MurmurRPC__pb2.Authenticator.Request.SerializeToString,
      ),
      'DatabaseUserQuery': grpc.unary_unary_rpc_method_handler(
          servicer.DatabaseUserQuery,
          request_deserializer=MurmurRPC__pb2.DatabaseUser.Query.FromString,
          response_serializer=MurmurRPC__pb2.DatabaseUser.List.SerializeToString,
      ),
      'DatabaseUserGet': grpc.unary_unary_rpc_method_handler(
          servicer.DatabaseUserGet,
          request_deserializer=MurmurRPC__pb2.DatabaseUser.FromString,
          response_serializer=MurmurRPC__pb2.DatabaseUser.SerializeToString,
      ),
      'DatabaseUserUpdate': grpc.unary_unary_rpc_method_handler(
          servicer.DatabaseUserUpdate,
          request_deserializer=MurmurRPC__pb2.DatabaseUser.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'DatabaseUserRegister': grpc.unary_unary_rpc_method_handler(
          servicer.DatabaseUserRegister,
          request_deserializer=MurmurRPC__pb2.DatabaseUser.FromString,
          response_serializer=MurmurRPC__pb2.DatabaseUser.SerializeToString,
      ),
      'DatabaseUserDeregister': grpc.unary_unary_rpc_method_handler(
          servicer.DatabaseUserDeregister,
          request_deserializer=MurmurRPC__pb2.DatabaseUser.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'DatabaseUserVerify': grpc.unary_unary_rpc_method_handler(
          servicer.DatabaseUserVerify,
          request_deserializer=MurmurRPC__pb2.DatabaseUser.Verify.FromString,
          response_serializer=MurmurRPC__pb2.DatabaseUser.SerializeToString,
      ),
      'RedirectWhisperGroupAdd': grpc.unary_unary_rpc_method_handler(
          servicer.RedirectWhisperGroupAdd,
          request_deserializer=MurmurRPC__pb2.RedirectWhisperGroup.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
      'RedirectWhisperGroupRemove': grpc.unary_unary_rpc_method_handler(
          servicer.RedirectWhisperGroupRemove,
          request_deserializer=MurmurRPC__pb2.RedirectWhisperGroup.FromString,
          response_serializer=MurmurRPC__pb2.Void.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'MurmurRPC.V1', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
